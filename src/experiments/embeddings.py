from typing import List, Literal

import sentencepiece as spm

from constants import CORPUS_TYPE, SRC, TRG, VOCAB_SIZE


def model_generation(sources: List[str], lang: Literal["osh", "eng"]):
    spm.SentencePieceTrainer.Train(
        split_by_whitespace=True,
        input=sources,
        model_type="bpe",
        model_prefix=f"{lang}-{CORPUS_TYPE}-{VOCAB_SIZE}",
        vocab_size=VOCAB_SIZE,
        character_coverage=0.98,
    )


def corpus_encoding(sources: List[str], lang: Literal["osh", "eng"]):
    sp = spm.SentencePieceProcessor(
        model_file=f"{lang}-{CORPUS_TYPE}-{VOCAB_SIZE}.model",
        add_bos=True,
        add_eos=True,
        out_type=str,
    )
    with open(
        f"encoded-{lang}-{CORPUS_TYPE}-{VOCAB_SIZE}.txt", "w", encoding="utf-8"
    ) as encoded_corpus:
        for file_name in sources:
            with open(file_name, "r", encoding="utf-8") as corpus:
                for line in corpus:
                    encoded_line = " ".join(str(x) for x in sp.encode(line))
                    encoded_corpus.write(encoded_line.strip() + "\n")


print(f"Generating {SRC} model...")
model_generation([f"corpus-{SRC}.txt"], SRC)
print(f"Encoding {SRC} corpus...")
corpus_encoding([f"corpus-{SRC}.txt"], SRC)
print(f"Generating {TRG} model...")
model_generation([f"corpus-{TRG}.txt"], TRG)
print(f"Encoding {TRG} corpus...")
corpus_encoding([f"corpus-{TRG}.txt"], TRG)
print("Done!")
