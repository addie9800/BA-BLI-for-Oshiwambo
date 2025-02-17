import re
from itertools import tee
from typing import Iterator, List, Optional, Tuple, TypeVar

import pypdfium2 as pypdf  # type:ignore[import-untyped]

T = TypeVar("T")

START_PATTERN = r"(?<!(\.| )[a-z])(\.|!|\?)(\n|\r\n)"
WORD_PATTERN = (
    r"((?P<word>[,a-z:\s\(\)]*(\s*-\s*)?[,a-z\s'\(\)]+)(\/[^\.-]*?(\n|\r\n)?.*?\/)?)"
)
DETAILS_PATTERN = r"(?P<details>[,a-z: ]*(\s*-\s*)?[,A-z\s'\(\)-]+)?"
PHONETIC_SPACE_OR_INSERTION_PATTERN = (
    r"(?P<phonetic_insertion>(\/|\()[^\.-]*?(\n|\r\n)?.*?(\/|\()| |\s*-\s*)"
)
WORD_TYPE_PATTERN = r"(?P<word_type>(\s*((conj|n|a|(\(.*\) *)?v\s*(\.[ti&]){0,2}|adv|phr|prep|pl?\. *n)(\.|(\n|\r\n)))))"
PROPER_NOUN_PATTERN = (
    r"(?P<proper_noun>[A-Z][A-z -:]*?)"
    r"(?P<proper_noun_phonetic>(\/[^-\.]*?\/\s*((p\.\s*)?n\.)?|(((p\.\s*)?n|a)\.)))"
)
DICT_ENTRY_PATTERN = (
    rf"{START_PATTERN}("
    rf"{WORD_PATTERN}{DETAILS_PATTERN}{PHONETIC_SPACE_OR_INSERTION_PATTERN}{WORD_TYPE_PATTERN}|"
    rf"{PROPER_NOUN_PATTERN})"
)
COMPILED_DICT_PATTERN = re.compile(DICT_ENTRY_PATTERN)
NOUN_TRANSLATION = re.compile(
    r".*?(n\.)?\s*(?P<sing_prefix>[A-z]*\/)?"
    r"(?P<base>[A-z- ]+( |$|(?=,)|(?=\()))"
    r"(?P<plu_prefix>(\(([ A-z]*-\s*,?)+?\))?)"
    r"(?P<remains>[A-z ]*(?!/))"
)
VERB_TRANSLATION = re.compile(
    r"(?P<base>[a-z ]+)" r"(\((?P<conj_suffix>[a-z])\))?" r"(?P<remains>[a-z ]*)"
)


# If something goes wrong: https://regex101.com/r/Nff2a7/1

# NOTE that Oshindonga does not use the letter c. If it appears in a possible translation, it is very likely this is
# the result of inaccurate scanning and should be corrected.


def preprocess_text(pdf_text_page: pypdf.PdfTextPage) -> str:
    text = pdf_text_page.get_text_bounded(bottom=0.05 * page_height)
    # Remove or replace abbreviations
    text = re.sub(r"(/| )swh\.", " somewhere ", text)
    text = re.sub(r"(/| )os\.", " oneself ", text)
    text = re.sub(r"\(conj\.\)", "conj.", text)
    text = re.sub(r"11", "n", text)
    return re.sub(r"", "-", text)


def fix_common_ndonga_parsing_errors(text: str) -> str:
    # Remove all - that work as connectors to the next line
    text = re.sub(r"\s", " ", text)
    text = re.sub("  +", " ", text)
    # Replace comon parse errors
    text = re.sub(r"c", "e", text)
    text = re.sub(r"0", "o", text)
    return re.sub(r"(?<=[a-z])J", "d", text)


def peek(iterator: Iterator[T]) -> Optional[T]:
    _, skippable_iterator = tee(iterator)
    return next(skippable_iterator, None)


def export_entries(text: str) -> Iterator[Tuple[str, List[str]]]:
    previous_word = ""
    for entry in (iterator := re.finditer(COMPILED_DICT_PATTERN, text)):
        start, end = entry.span()
        next_entry = peek(iterator)
        start_next, _ = next_entry.span() if next_entry else (len(entry.string) + 1, 0)
        full_entry = text[start:start_next]
        if not full_entry and full_entry.count(".") < 2:
            # It cannot be guaranteed that the last entry is completely extracted, which why it hast to be skipped, if
            # it does not contain two periods (usually indicating the end of an entry)
            break
        full_entry = re.sub(r"-\s*\r?\n(?!\))", " ", full_entry)
        full_entry = re.sub(r"(\r?\n)", " ", full_entry)
        if word_type := entry["word_type"] or entry["proper_noun"]:
            translation_entry = full_entry[end - start - 1 :]
            sing_translations: List[str] = list()
            plu_translations: List[str] = list()
            counter = 0
            for option in re.split(r"[0-9]\.", translation_entry.removeprefix(".")):
                counter += 1
                if not option.strip():
                    continue
                if counter > 2:
                    # Restrict to 2 options per entry. Usually the options get complexer, leading to parsing errors and
                    # low quality translations
                    break
                if option.startswith("&"):
                    translated_word = option.split(".")[1]
                else:
                    translated_word = option.split(".")[0]
                # if 'jet plane' in full_entry:
                #    breakpoint()
                if ("n" in word_type and "conj" not in word_type) or entry[
                    "proper_noun"
                ]:
                    singular_translation = fix_common_ndonga_parsing_errors(
                        translated_word
                    )
                    translation_matches = re.findall(
                        NOUN_TRANSLATION, singular_translation
                    )
                    if not translation_matches:
                        breakpoint()
                    for match in translation_matches:
                        base = match[2].strip()
                        sing_prefix = match[1].removesuffix("/").strip()
                        remains = match[-1]
                        plu_prefixes = re.sub(r"([()\-])", "", match[4])
                        if sing := (sing_prefix + base + remains).strip():
                            sing_translations.append(sing)
                        if plu_prefixes:
                            for plu_prefix in plu_prefixes.split(","):
                                plu_translations.append(
                                    (plu_prefix.strip() + base + remains).strip()
                                )
                elif "v" in word_type:
                    if "attack" in full_entry:
                        breakpoint()
                    translations = fix_common_ndonga_parsing_errors(translated_word)
                    translation_matches = re.findall(VERB_TRANSLATION, translations)
                    if not translation_matches:
                        breakpoint()
                    for match in translation_matches:
                        base = match[0].strip()
                        if not base:
                            break
                        conj_suffix = match[2].strip()
                        remains = match[3].strip()
                        if remains:
                            remains = " " + remains
                        sing_translations.append(base + remains)
                        if conj_suffix:
                            sing_translations.append(base[:-1] + conj_suffix + remains)
                elif "conj" in word_type:
                    print("haha")
            words = entry["word"]
            if not words:
                words = entry["proper_noun"]
            for word in words.split(","):
                word = re.sub(r"(?s)\(.*", "", word)
                word = word.strip()
                if len(word) < 2:
                    # This is probably a parsing error
                    continue
                # Sometimes if variations of one word are in the dictionary, this is indicated by a ~, which is
                # incorrectly parsed to be -
                word = re.sub(" - ", " " + previous_word + " ", word)
                previous_word = word
                if sing_translations:
                    yield word, sing_translations
                if plu_translations:
                    word = re.sub(r"(?<!(a|e|i|o|u))y$", "ie", word) + "s"
                    yield word, plu_translations


doc = pypdf.PdfDocument("ndonga english 1996 2.pdf")
cnt = 0
for i in range(0, len(doc)):
    page = doc[i]
    page_height = page.get_height()
    text_page = page.get_textpage()
    # Extract Text without page numbers
    text_on_text_page = preprocess_text(text_page)
    for word, translation in export_entries(text_on_text_page):
        cnt += 1
        print(f"{word}: {translation}")
print(cnt)
