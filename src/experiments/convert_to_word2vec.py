from pathlib import Path

import numpy as np
import pandas as pd
from flair.data import Sentence
from flair.embeddings import BytePairEmbeddings as BPE
from flair.embeddings import WordEmbeddings as WordEmb

from constants import EMBEDDING_DIMENSION
from graph_matching import word_order_by_frequency

lang = "swa"
corpus_type = "small"
vocab_size = 20000
base_path = Path(__file__).resolve().parent
word_list = word_order_by_frequency(lang, n=3000)

# embedding = BPE(
# model_file_path=base_path / f"{lang}-{corpus_type}-{vocab_size}.model",
# embedding_file_path=base_path
#                        / f"ordered-{lang}-{corpus_type}-{vocab_size}-embeddings.txt",
#    dim=EMBEDDING_DIMENSION,
#    preprocess=False,
# )

embedding = WordEmb(f"embeddings-{lang}-test.glove.txt")


def get_embedding(word):
    if not word:
        raise ValueError("Trying to get embedding for empty word")
    sentence = Sentence(word)
    embedding.embed(sentence)
    return sentence[0].embedding.cpu().numpy()  # Convert Flair embedding to NumPy array


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

# vvv This part was created with help of ChatGPT vvv

with open(f"{lang}.word2vec", "w") as file:
    file.write("3000 300\n")
    for i in range(0, len(embeddings_column)):
        file.write(f"{word_list[i]} {' '.join(map(str, embeddings_column[i]))}\n")
