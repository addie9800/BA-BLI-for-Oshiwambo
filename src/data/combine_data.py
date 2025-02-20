from pathlib import Path
from typing import Literal

base_path = Path(__file__).resolve().parent


def create_corpus(lang: Literal["eng", "osh"]):
    data = [#base_path / "fundus" / f"articles_{lang}.txt",
            #base_path / "constitution" / f"constitution_{lang}.txt",
            #base_path / "other" / f"other_sources_{lang}.txt"
            ] + ([base_path / "fundus" / "articles_swa.txt"] if lang == "swa" else [base_path / "fundus" / "articles_eng_tz.txt"])
    with open(base_path.parent / "experiments" / f"corpus-{lang}.txt", "w") as corpus:
        for file_name in data:
            with open(file_name, "r") as file:
                for line in file:
                    corpus.write(line)


create_corpus("eng")
create_corpus("swa")
