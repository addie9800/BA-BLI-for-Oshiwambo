import json
import statistics
import sys

sys.path.extend(
    [
        "/vol/fob-vol3/nebenf20/breidina/Dokumente/BLI-for-Oshiwambo",
        "/vol/fob-vol3/nebenf20/breidina/Dokumente/BLI-for-Oshiwambo/goat/GoatForBli",
    ]
)

import argparse
import random

import goat.GoatForBli.proc_v_sgm as proc_v_sgm
import numpy as np
from src.experiments.constants import (EMBEDDING_DIMENSION,
                                       FINAL_DICTIONARY_SIZE,
                                       ITERATIVE_SOFTSGM_ITERS,
                                       PROGRUSTES_ITERS, SOFTSGM_ITERS, SRC,
                                       TRG)
from src.experiments.graph_matching import (get_seeds,
                                            load_embeddings_into_matrix,
                                            match_translations,
                                            word_order_by_frequency)
from tqdm import tqdm

# This file is inspired by https://github.com/kellymarchisio/goat-for-bli/tree/main (Marchisio 2022)
# Primarily by the file combo.py

parser = argparse.ArgumentParser(description="Process some integers.")
parser.add_argument(
    "--vocab_size", type=int, required=True, help="Size of the vocabulary"
)
parser.add_argument("--corpus_type", type=str, required=True, help="Type of the corpus")
parser.add_argument("--num_seeds", type=int, required=True, help="Number of seeds")
parser.add_argument(
    "--end_proc", type=str, required=True, help="Whether to run Procrustes first"
)

args = parser.parse_args()
VOCAB_SIZE = args.vocab_size
CORPUS_TYPE = args.corpus_type
NUM_SEEDS = args.num_seeds
END_PROC = bool(eval(args.end_proc))
assert CORPUS_TYPE in ["small", "extended"]

best_score = 0
best_hypotheses = []
best_params = (0, 0, 0, 0)

print("Getting words...")
word_list_osh = word_order_by_frequency(SRC, FINAL_DICTIONARY_SIZE)
word_list_eng = word_order_by_frequency(TRG, FINAL_DICTIONARY_SIZE)
identical_words = set(word_list_osh) & set(word_list_eng)
for word in identical_words:
    if len(word) > 3:
        word_list_eng.remove(word)
        word_list_osh.remove(word)
assert len(word_list_eng) == len(word_list_osh)
print("Creating Graphs...")
osh_df, osh_graph = load_embeddings_into_matrix(
    SRC, word_list_osh, vocab_size=VOCAB_SIZE, corpus_type=CORPUS_TYPE
)  # osh_graph = xxT in combo.py
eng_df, eng_graph = load_embeddings_into_matrix(
    TRG, word_list_eng, vocab_size=VOCAB_SIZE, corpus_type=CORPUS_TYPE
)  # eng_graph = yyT in combo.py
assert osh_graph.shape == eng_graph.shape == (len(word_list_osh), len(word_list_osh))
if not (
    osh_df["embedding"].get(0).shape
    == eng_df["embedding"].get(0).shape
    == (EMBEDDING_DIMENSION,)
):
    raise ValueError(
        "Embedding dimensions do not match. Did you update the flair token.py file?"
    )
print("Getting seeds...")
seed_list = [(x, y) for x, y in get_seeds(word_list_osh, word_list_eng)]
# there is close to no overlap in words for the two languages, this allows us to map names to each-other
name_seed_list = []
for word in word_list_eng:
    if word in word_list_osh and len(word) > 3:
        x, y = word_list_osh.index(word), word_list_eng.index(word)
        duplicate = False
        for a, b in seed_list:
            if x == a or y == b:
                duplicate = True
        if not duplicate:
            name_seed_list.append((x, y))

# When using a system combination, it is best to start with Procrustes and GOAT, for very low and very
# high numbers of seeds. Hence, we start with Procrustes

rng_values = [2000 + i + 20 for i in range(10)]
scores = []

for j in tqdm(range(10)):
    random.Random(rng_values[j]).shuffle(seed_list)
    random.shuffle(seed_list)
    train_seeds = seed_list[:NUM_SEEDS] + name_seed_list
    dev_seeds = seed_list[NUM_SEEDS:]
    gold_osh_train_indices, gold_eng_train_indices = proc_v_sgm.unzip_pairs(train_seeds)
    sgm_hypotheses_osh = []
    sgm_hypotheses_eng = []
    graph_matching_options = dict(
        shuffle_input=True,
        maximize=True,
        P0="barycenter",
    )  # rng=rng_values[j])
    osh_embeddings = np.stack(osh_df["embedding"].values)
    eng_embeddings = np.stack(eng_df["embedding"].values)
    hypotheses = []
    for i in range(20):
        print(f"Starting Iteration {i}")

        if END_PROC:
            # Run Graph Matching with input from Procrustes

            _, _, sgm_hypotheses_int = proc_v_sgm.iterative_softsgm(
                x_sim=osh_graph,
                y_sim=eng_graph,
                input_x_seed_inds=sgm_hypotheses_osh,
                input_y_seed_inds=sgm_hypotheses_eng,
                gold_x_seed_inds=gold_osh_train_indices,
                gold_y_seed_inds=gold_eng_train_indices,
                softsgm_iters=SOFTSGM_ITERS,
                k=1,
                val_set=dev_seeds,
                curr_i=1,
                total_i=ITERATIVE_SOFTSGM_ITERS,
                run_reverse=True,
                function="goat",
                opts=graph_matching_options,
            )
            sgm_hypotheses_osh, sgm_hypotheses_eng = proc_v_sgm.unzip_pairs(
                sgm_hypotheses_int
            )

            # Run Procrustes
            (
                hypotheses,
                _,
                procrustes_hypotheses_int,
                _,
                _,
                ranked_hypotheses,
            ) = proc_v_sgm.iterative_procrustes_w_csls(
                x=osh_embeddings,
                y=eng_embeddings,
                input_x_seed_inds=sgm_hypotheses_osh,
                input_y_seed_inds=sgm_hypotheses_eng,
                gold_x_seed_inds=gold_osh_train_indices,
                gold_y_seed_inds=gold_eng_train_indices,
                val_set=dev_seeds,
                total_i=PROGRUSTES_ITERS,
                k=1,
            )
            sgm_hypotheses_osh, sgm_hypotheses_eng = proc_v_sgm.unzip_pairs(
                procrustes_hypotheses_int
            )

        else:
            # Run Procrustes

            (
                _,
                _,
                procrustes_hypotheses_int,
                _,
                _,
                ranked_hypotheses,
            ) = proc_v_sgm.iterative_procrustes_w_csls(
                x=osh_embeddings,
                y=eng_embeddings,
                input_x_seed_inds=sgm_hypotheses_osh,
                input_y_seed_inds=sgm_hypotheses_eng,
                gold_x_seed_inds=gold_osh_train_indices,
                gold_y_seed_inds=gold_eng_train_indices,
                val_set=dev_seeds,
                total_i=PROGRUSTES_ITERS,
                k=1,
            )
            sgm_hypotheses_osh, sgm_hypotheses_eng = proc_v_sgm.unzip_pairs(
                procrustes_hypotheses_int
            )

            # Run Graph Matching with input from Procrustes

            hypotheses, _, sgm_hypotheses_int = proc_v_sgm.iterative_softsgm(
                x_sim=osh_graph,
                y_sim=eng_graph,
                input_x_seed_inds=sgm_hypotheses_osh,
                input_y_seed_inds=sgm_hypotheses_eng,
                gold_x_seed_inds=gold_osh_train_indices,
                gold_y_seed_inds=gold_eng_train_indices,
                softsgm_iters=SOFTSGM_ITERS,
                k=1,
                val_set=dev_seeds,
                curr_i=1,
                total_i=ITERATIVE_SOFTSGM_ITERS,
                run_reverse=True,
                function="goat",
                opts=graph_matching_options,
            )
            sgm_hypotheses_osh, sgm_hypotheses_eng = proc_v_sgm.unzip_pairs(
                sgm_hypotheses_int
            )

    # Evaluation

    print("Evaluating")
    dev_src_inds, dev_trg_inds = proc_v_sgm.unzip_pairs(dev_seeds)
    dev_hypotheses = set(hyp for hyp in hypotheses if hyp[0] in dev_src_inds)
    matches, precision, recall = proc_v_sgm.eval(dev_hypotheses, dev_seeds)
    print(
        "\tDev Pairs matched: {0} \n\t(Precision; {1}%) (Recall: {2}%)".format(
            len(matches), precision, recall
        ),
        flush=True,
    )
    scores.append(precision)
    if precision > best_score:
        best_score = precision
        best_hypotheses = hypotheses - (set(train_seeds) & hypotheses)
        best_ranked_hypotheses = []
        for x, y, val in ranked_hypotheses:
            if x in gold_osh_train_indices:
                continue
            best_ranked_hypotheses.append((x, y))
        best_params = (NUM_SEEDS, VOCAB_SIZE, END_PROC, CORPUS_TYPE)
with open(f"stats-{CORPUS_TYPE}.txt", "a") as file:
    file.write(
        f"{NUM_SEEDS}-{VOCAB_SIZE}-{END_PROC}-average score: {statistics.mean(scores)}, std-dev: {statistics.stdev(scores)}\n"
    )
final_dictionary = match_translations(osh_df, eng_df, best_hypotheses)
with open(
    f"dictionary-no-names-{best_params[0]}-{best_params[1]}-{best_params[2]}-{best_params[3]}-{best_score}.json",
    "w",
    encoding="utf-8",
) as file:
    file.write(json.dumps(final_dictionary))
ranked_dictionary = match_translations(osh_df, eng_df, best_ranked_hypotheses)
with open(
    f"dictionary-no-names-{best_params[0]}-{best_params[1]}-{best_params[2]}-{best_params[3]}-{best_score}-ranked.json",
    "w",
    encoding="utf-8",
) as file:
    file.write(json.dumps(ranked_dictionary))
print("Done!")
