from typing import Dict, List, Literal, Tuple

import numpy as np
from gensim.models import keyedvectors

from constants import CORPUS_TYPE, EMBEDDING_DIMENSION, SRC, TRG, VOCAB_SIZE


def get_vocab(lang: Literal["osh", "eng"]) -> List[str]:
    with open(
        f"{lang}-{CORPUS_TYPE}-{VOCAB_SIZE}.vocab", "r", encoding="utf-8"
    ) as file:
        vocab = []
        for line in file:
            parts = line.strip().split("\t")
            if parts:
                word = parts[0]
                vocab.append(word)
    return vocab


def load_glove_embeddings(lang: Literal["osh", "eng"]) -> Dict[str, np.ndarray]:
    # This function was created with the help of ChatGPT
    glove_embeddings = {}
    with open(
        f"embeddings-{lang}-{CORPUS_TYPE}-{VOCAB_SIZE}.glove.txt", "r", encoding="utf-8"
    ) as file:
        for line in file:
            parts = line.split()
            word = parts[0]
            if (
                len(vector := np.array(parts[1:], dtype=np.float32))
                == EMBEDDING_DIMENSION
            ):
                glove_embeddings[word] = vector
    return glove_embeddings


def reorder_glove_embeddings(
    lang: Literal["osh", "eng"],
    vocab: List[Tuple[str, int]],
    glove_embeddings: Dict[int, np.ndarray],
) -> List[Tuple[str, np.ndarray]]:
    # This function was created with the help of ChatGPT
    reordered_embeddings = []
    glove_keyed_vectors = keyedvectors.KeyedVectors.load_word2vec_format(
        f"embeddings-{lang}-{CORPUS_TYPE}-{VOCAB_SIZE}.glove.txt"
    )
    v = glove_keyed_vectors.vectors
    for word in vocab:
        if word in glove_embeddings:
            embedding = glove_embeddings[word]
        else:
            embedding = v.std() * np.random.randn(v.shape[1]) + v.mean()
        reordered_embeddings.append((word, embedding))
    return reordered_embeddings


def save_reordered_embeddings(
    lang: Literal["eng", "osh"], embeddings: List[Tuple[str, np.ndarray]]
) -> None:
    with open(
        f"ordered-{lang}-{CORPUS_TYPE}-{VOCAB_SIZE}-embeddings.txt",
        "w",
        encoding="utf-8",
    ) as file:
        # This function was created with the help of ChatGPT
        file.write(f"{len(embeddings)} {len(embeddings[0][1])}\n")
        for word, embedding in embeddings:
            embedding_str = " ".join(map(str, embedding))
            file.write(f"{word} {embedding_str}\n")


def convert_embeddings(lang: Literal["osh", "eng"]):
    sp_vocab = get_vocab(lang)
    gl_embs = load_glove_embeddings(lang)
    ordered_embs = reorder_glove_embeddings(lang, sp_vocab, gl_embs)
    save_reordered_embeddings(lang, ordered_embs)


# This is necessary, since GloVe reorders the embeddings and for BPE to work correctly, we need the original ordering
# restored

convert_embeddings(SRC)
convert_embeddings(TRG)
