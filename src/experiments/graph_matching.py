import argparse
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

import json5
import numpy as np
import pandas as pd
from flair.data import Sentence
from flair.embeddings import BytePairEmbeddings as BPE
from flair.embeddings import WordEmbeddings as WordEmb
from pandas import Series
# from pkg.gmp import quadratic_assignment_ot
from scipy.optimize import OptimizeResult
from tqdm import tqdm

from constants import (EMBEDDING_DIMENSION, FINAL_DICTIONARY_SIZE, NUM_SEEDS,
                       SRC, TRG)


def load_embeddings_into_matrix(
    lang: Literal["eng", "osh"],
    word_list: List[str],
    corpus_type: str = "small",
    vocab_size: int = 10000,
) -> Tuple[pd.DataFrame, np.ndarray]:
    base_path = Path(__file__).resolve().parent
    embedding = BPE(
        model_file_path=base_path / f"{lang}-{corpus_type}-{vocab_size}.model",
        embedding_file_path=base_path
        / f"ordered-{lang}-{corpus_type}-{vocab_size}-embeddings.txt",
        dim=EMBEDDING_DIMENSION,
        preprocess=False,
    )
    # embedding = WordEmb(f'embeddings-{lang}-test.glove.txt')

    def get_embedding(word):
        if not word:
            raise ValueError("Trying to get embedding for empty word")
        sentence = Sentence(word)
        embedding.embed(sentence)
        return (
            sentence[0].embedding.cpu().numpy()
        )  # Convert Flair embedding to NumPy array

    # Create a DataFrame with words and their embeddings
    data = {"word": word_list, "embedding": [get_embedding(word) for word in word_list]}
    df = pd.DataFrame(data)
    embeddings_column = df["embedding"]
    # According to (Marchisio 2022) we should normalize, mean-center and re-normalize
    embeddings_column = embeddings_column.apply(lambda emb: emb / np.linalg.norm(emb))
    embeddings_mean = embeddings_column.mean()
    embeddings_column = embeddings_column.apply(lambda emb: emb - embeddings_mean)
    embeddings_column = embeddings_column.apply(lambda emb: emb / np.linalg.norm(emb))
    embedding_matrix = np.zeros((len(embeddings_column), len(embeddings_column[0])))
    df["embedding"] = embeddings_column
    for i in range(0, len(embeddings_column)):
        embedding_matrix[i] = embeddings_column[i]
    return df, embedding_matrix @ embedding_matrix.T


# def graph_matching(
#    graph_eng: np.ndarray, graph_osh: np.ndarray, seeds: np.ndarray
# ) -> OptimizeResult:
#    options = {
#        "maximize": True,
#        "maxiter": 500,
#        "shuffle_input": True,
#        "tol": 1e-6,
#        "reg": 500,  # As in (Marchisio 2022)
#        "partial_match": seeds,
#    }
#    return max(
#        [
#            quadratic_assignment_ot(graph_osh, graph_eng, options=options)
#            for k in tqdm(range(4))
#        ],
#        key=lambda x: x.fun,
#    )


def get_seeds(osh_words: List[str], eng_words: List[str]) -> np.ndarray:
    with open(
        # Path(__file__).resolve().parent.parent
        # / "data"
        # / "dictionaries"
        # / "1986"
        # / "all_translations.json",
        f"translations-{SRC}-{TRG}.json",
        "r",
        encoding="utf-8",
    ) as file:
        all_translations: Dict[str, List[str]] = json5.load(file)
    seeds = list()
    eng_seeds = set()
    osh_seeds = set()
    for word in tqdm(osh_words):
        translation_candidates = all_translations.get(word)
        if not translation_candidates:
            continue
        if available_translations := set(translation_candidates) & set(eng_words):
            osh_seed = word
            for eng_seed in available_translations:
                # eng_seed = available_translations.pop()
                if (
                    osh_seed in osh_words
                    and eng_seed in eng_words
                    and osh_seed not in osh_seeds
                    and eng_seed not in eng_seeds
                ):
                    eng_seeds.add(eng_seed)
                    osh_seeds.add(osh_seed)
                    seeds.append([osh_words.index(osh_seed), eng_words.index(eng_seed)])
                    break
    return np.array(seeds)


def match_translations(
    osh: pd.DataFrame,
    eng: pd.DataFrame,
    mapping: np.ndarray,
) -> Dict[str, List[str]]:
    osh_words: Series[str] = osh["word"]
    eng_words: Series[str] = eng["word"]
    translations = defaultdict(list)
    for i, j in mapping:
        if word := eng_words.get(j):
            translations[osh_words.get(i)].append(word)
    return translations


def word_order_by_frequency(
    lang: Literal["eng", "osh"], n: Optional[int] = None
) -> List[str]:
    frequencies: Counter = Counter()
    with open(f"corpus-{lang}.txt", "r", encoding="utf-8") as file:
        for line in file:
            line = line.replace("\n", "")
            line = re.sub(r"\s*[A-z-]*0[A-z-]*\s*", " ", line)
            frequencies.update(
                [word for word in line.split(" ") if word and not word == 0]
            )
    return [word for word, _ in frequencies.most_common(n)]


# if __name__ == "__main__":
#    parser = argparse.ArgumentParser(description="Process some integers.")
#    parser.add_argument(
#        "--vocab_size", type=int, required=True, help="Size of the vocabulary"
#    )
#    parser.add_argument(
#        "--corpus_type", type=str, required=True, help="Type of the corpus"
#    )
#    args = parser.parse_args()
#    VOCAB_SIZE = args.vocab_size
#    CORPUS_TYPE = args.corpus_type
#    assert CORPUS_TYPE in ["small", "extended"]
#    dimension = EMBEDDING_DIMENSION
#    dictionary_size = FINAL_DICTIONARY_SIZE
#    print("Getting words...")
#    word_list_osh = word_order_by_frequency(SRC, dictionary_size)
#    word_list_eng = word_order_by_frequency(TRG, dictionary_size)
#    assert len(word_list_eng) == len(word_list_osh) == dictionary_size
#    print("Creating Graphs...")
#    osh_df, osh_graph = load_embeddings_into_matrix(SRC, word_list_osh)
#    eng_df, eng_graph = load_embeddings_into_matrix(TRG, word_list_eng)
#    assert osh_graph.shape == eng_graph.shape == (dictionary_size, dictionary_size)
#    # The factor of 2 is needed to comply with the output from flair -- https://github.com/flairNLP/flair/issues/724
#    assert (
#        osh_df["embedding"].get(0).shape
#        == eng_df["embedding"].get(0).shape
#        == (dimension,)
#    )
#    print("Getting seeds...")
#    seed_list = get_seeds(word_list_osh, word_list_eng)
#    print(len(seed_list))
#    print("Computing mapping...")
#    optimal_mapping = graph_matching(
#        eng_graph, osh_graph, np.random.permutation(seed_list)[:NUM_SEEDS]
#    ).col_ind
#    mapping = []
#    for row in enumerate(optimal_mapping):
#        mapping.append(row)
#    final_dictionary = match_translations(osh_df, eng_df, mapping)
#    with open("dictionary.json", "w", encoding="utf-8") as file:
#        file.write(str(final_dictionary))
#    print("Done!")
