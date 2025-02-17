import json
import math
import re
from typing import Iterator, List, Optional, Tuple, TypeVar

import pdfplumber.page
import tqdm
from pdfplumber import open as open_pdf

T = TypeVar("T")
ENTRY_SELECTOR = re.compile(
    r"(?m)^(?P<prefix>[a-z]*(?=\/))?\/?(?P<word>[a-z -!]+?)"
    r"(\s*([=,])\s*(?P<equiv>.*?);?)?"
    r"((?P<space> ?)\((?P<details>[a-z-, \.]+)\))?\s*"
    r"\|(?P<translations>[^\n>]*)"
)
COMMON_ABBREVIATIONS = {
    " abbr.": " abbreviation",
    " adv.": "",
    " anat.": " anatomy",
    " appr.": " approximately",
    " arith.": " arithmetics",
    " cf.": " collectively",
    " conc.": " concord",
    " derog.": " derogatory",
    " dim.": " diminutive",
    " fem.": " feminine",
    " e.o.": " each other",
    " esp.": " especially",
    " Her.": " Herero",
    " int.": " interjection",
    " masc.": " masculine",
    " math.": " mathematical",
    " n.": "",
    " neg.": " negative",
    " obj.": "",
    " orig.": " originally",
    " pass.": "",
    " phr.": "",
    " p.": " person",
    " pl.": "",
    " poss.": "",
    " pron.": "",
    " prov.": "",
    " rel.": "",
    " sb.": " somebody",
    " sth.": " something",
    " subj.": "",
    " swh.": " somewhere",
    " th.": " thing",
    " theol.": " theology",
    " v.": "",
    " v.i.": "",
    " v.t.": "",
    " zool.": " zoological",
}


def preprocess_text(text: str) -> str:
    abbreviation_pattern = re.compile(
        "|".join(map(re.escape, COMMON_ABBREVIATIONS.keys()))
    )
    text = re.sub(r"([-])\n\s*", "", text)
    text = re.sub(r"!\n", ".\n", text)
    text = re.sub(r"(?<!\.)\n", " ", text)
    text = text.replace('"', "")
    text = abbreviation_pattern.sub(
        lambda match: COMMON_ABBREVIATIONS[match.group(0)], text
    )
    return text.lower()


def split_word_and_translation(
    page_fragment: pdfplumber.page.Page,
) -> pdfplumber.page.Page:
    current_font = ""
    for i in range(0, len(page_fragment.chars) - 1):
        letter = page_fragment.chars[i]
        if (
            current_font == "TimesNewRomanPS-BoldMT"
            and letter["fontname"] == "TimesNewRomanPSMT"
            and page_fragment.chars[i + 1]["fontname"] == "TimesNewRomanPSMT"
        ):
            # If font changes to not bold: the translation starts
            letter["text"] = "|" + letter["text"]
            current_font = letter["fontname"]
        elif (
            current_font == "TimesNewRomanPS-BoldMT"
            and letter["fontname"] == "TimesNewRomanPSMT"
            and not page_fragment.chars[i + 1]["fontname"] == "TimesNewRomanPSMT"
        ):
            # If there is just one letter in another font, this is usually an equal sign, which does not indicate
            # a language change
            pass
        elif (
            current_font == "TimesNewRomanPSMT"
            and letter["fontname"] == "TimesNewRomanPS-BoldMT"
            and math.isclose(
                letter["y0"], page_fragment.chars[i - 1]["y0"], abs_tol=0.5
            )
        ):
            # In this case there is additional Oshindonga in this line, we do no want to parse this and add a special
            # character to recognise this case in later processing
            letter["text"] = ">" + letter["text"]
            current_font = letter["fontname"]
        else:
            current_font = letter["fontname"]
    return page_fragment


def extract_text_from_page(page_to_be_extracted: pdfplumber.page.Page) -> str:
    def font_based_filtering(obj):
        fonts = ["TimesNewRomanPS-BoldMT", "TimesNewRomanPSMT"]
        return obj["object_type"] == "char" and obj["fontname"] in fonts

    left = page_to_be_extracted.crop(
        (
            0,
            0.06 * float(page_to_be_extracted.height),
            0.493 * float(page_to_be_extracted.width),
            0.93 * float(page_to_be_extracted.height),
        )
    )
    right = page_to_be_extracted.crop(
        (
            0.507 * float(page_to_be_extracted.width),
            0.06 * float(page_to_be_extracted.height),
            page_to_be_extracted.width,
            0.93 * float(page_to_be_extracted.height),
        )
    )
    cleaned_left = left.filter(font_based_filtering)
    cleaned_right = right.filter(font_based_filtering)
    return preprocess_text(
        split_word_and_translation(cleaned_left).extract_text()
        + "\n"
        + split_word_and_translation(cleaned_right).extract_text()
    )


def export_entries(text: str) -> Iterator[Tuple[str, List[str]]]:
    for entry in re.split(r"\.\n", text):
        current_translation_list: List[str] = list()
        match = re.search(ENTRY_SELECTOR, entry)
        if not match:
            continue
        prefix = match.group("prefix")
        word = match.group("word").strip()
        word = word.replace("!", "")
        details = match.group("details")
        # Remove all remarks
        translations = re.sub(r"\s*\(.*?\)\s*", " ", match.group("translations"))
        translations = re.sub(r"\..*", "", translations)
        translations = translations.replace("!", ",")
        equiv = match.group("equiv")
        if word.count(" ") > 2 or (equiv and equiv.count(" ") > 4):
            # This is likely a sentence and should be skipped
            continue
        for translation in re.split(r"[,;]", translations):
            cleaned_translation = re.sub(r"[:]", "", translation)
            cleaned_translation = cleaned_translation.strip()
            if cleaned_translation:
                current_translation_list.append(cleaned_translation)
        if not current_translation_list:
            continue
        if "aatyaha" in entry:
            breakpoint()
        if prefix:
            current_word = (prefix.strip() + word).strip()
            yield current_word, current_translation_list
            if details:
                plural_translation_list = [
                    (
                        re.sub(r"(?<!(a|e|i|o|u))y$", "ie", sing_trans) + "s"
                        if not sing_trans.endswith("s")
                        else sing_trans
                    )
                    for sing_trans in current_translation_list
                ]
                for detail in details.split(","):
                    detail = detail.strip()
                    if detail.endswith("-"):
                        yield detail.removesuffix("-") + word, plural_translation_list
                    elif detail.endswith("..."):
                        suffix = detail[-5:-3]
                        suffix_start = word.find(suffix)
                        if suffix_start == -1:
                            continue
                        else:
                            yield (
                                detail[:-5] + word[suffix_start:]
                            ).strip(), plural_translation_list
                    elif not match.group("space"):
                        yield current_word + detail.strip(), current_translation_list
                    else:
                        yield detail, current_translation_list
        elif word.startswith("-"):
            yield word[1:], current_translation_list
        else:
            yield word, current_translation_list
            if details:
                word_base = word[:-1]
                for detail in details.split(","):
                    detail = detail.strip()
                    if detail.endswith("-"):
                        yield detail[:-1] + word, current_translation_list
                    elif word.endswith(detail):
                        yield word + detail, current_translation_list
                    else:
                        yield word_base + detail, current_translation_list
        if equiv:
            yield re.sub(r"/", "", equiv), current_translation_list


def merge_dictionaries():
    import json5

    with open(r"translations.json", "r", encoding="utf-8") as json_file:
        data1 = json5.load(json_file)
    with open(r"translations 2.json", "r", encoding="utf-8") as json_file:
        data2 = json5.load(json_file)
    with open(r"all_translations.json", "w", encoding="utf-8") as json_file:
        json_file.write(str(data1 | data2))


file_to_parse = "ndonga dict tirronen.pdf"
seed_dictionary = {}
with open_pdf(file_to_parse) as pdf:
    for i in tqdm.tqdm(range(0, 1)):
        page = pdf.pages[i]
        page_text = extract_text_from_page(page)
        for word, translations in export_entries(page_text):
            seed_dictionary[word] = translations
with open("translations.json", "w") as json_file:
    json_file.write(json.dumps(seed_dictionary))
