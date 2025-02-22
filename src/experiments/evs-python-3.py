# modified from https://github.com/cambridgeltl/iso-study/blob/master/scripts/evs_script.py
# converted to python 3 using ChatGPT

import operator
import sys
import time

import networkx
import networkx.algorithms.isomorphism as iso
import numpy as np
from scipy.spatial.distance import cosine
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import normalize

# Pruning parameter
FREQ = 10000


def load_word_vectors(file_destination):
    """
    This method loads the word vectors from the supplied file destination.
    It loads the dictionary of word vectors and prints its size and the vector
    dimensionality.
    """
    print("Loading vectors from", file_destination, file=sys.stderr)
    input_dic = {}

    with open(file_destination, "r", encoding="utf-8") as in_file:
        lines = in_file.readlines()

    words = []
    vectors = []
    for line in lines[1:]:
        item = line.strip().split()
        dkey = item.pop(0)
        words.append(dkey)
        vector = np.array(item, dtype="float32")
        vectors.append(vector)

    npvectors = np.vstack(vectors)

    # Length normalize
    npvectors = normalize(npvectors, axis=1, norm="l2")

    # Mean centering dimensionwise
    npvectors = npvectors - npvectors.mean(0)

    # Length normalize again
    npvectors = normalize(npvectors, axis=1, norm="l2")

    # Create the final dictionary
    for i in range(len(words)):  # Changed xrange to range
        word = words[i]
        vector = npvectors[i]
        input_dic[word] = vector

    print(len(input_dic), "vectors loaded from", file_destination, file=sys.stderr)
    return words, input_dic


### This function selects the correct k
def select_k(spectrum, minimum_energy=0.9):
    running_total = 0.0
    total = sum(spectrum)
    if total == 0.0:
        return len(spectrum)
    for i in range(len(spectrum)):
        running_total += spectrum[i]
        if running_total / total >= minimum_energy:
            return i + 1
    return len(spectrum)


def main():
    # Get vectors first and words sorted by frequency
    en_freq, en_vec = load_word_vectors(sys.argv[1])
    de_freq, de_vec = load_word_vectors(sys.argv[2])

    # Initialise neighborhood graphs
    en_G = networkx.Graph()
    de_G = networkx.Graph()

    # Prepare data for nearest neighbour retrieval
    en_keys = []
    en_pruned = []
    de_keys = []
    de_pruned = []
    for word in en_freq[:FREQ]:
        en_keys.append(word)
        en_pruned.append(en_vec[word])

    for word in de_freq[:FREQ]:
        de_keys.append(word)
        de_pruned.append(de_vec[word])

    # Get nearest neighbours
    nbrs_en = NearestNeighbors(n_neighbors=2, algorithm="ball_tree").fit(en_pruned)
    distances_en, indices_en = nbrs_en.kneighbors(en_pruned)

    nbrs_de = NearestNeighbors(n_neighbors=2, algorithm="ball_tree").fit(de_pruned)
    distances_de, indices_de = nbrs_de.kneighbors(de_pruned)

    for index in indices_en:
        en_G.add_edge(en_keys[index[0]], en_keys[index[1]])

    for index in indices_de:
        de_G.add_edge(de_keys[index[0]], de_keys[index[1]])

    laplacian1 = networkx.spectrum.laplacian_spectrum(en_G)
    laplacian2 = networkx.spectrum.laplacian_spectrum(de_G)

    k1 = select_k(laplacian1)
    k2 = select_k(laplacian2)
    k = min(k1, k2)

    similarity = sum((laplacian1[:k] - laplacian2[:k]) ** 2)

    print("Laplacian:", similarity)


# The code starts here
if __name__ == "__main__":
    main()
