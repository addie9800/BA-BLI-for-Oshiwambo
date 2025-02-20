# System Setup

- Install Python 3.9
- Install the required packages with `pip install -r requirements.txt`
- Download https://github.com/kellymarchisio/goat-for-bli and follow the setup instructions. Make sure to include this repository in your path.

  _Note: I only noticed the remark about the bug when setting up this repository for the publication. The experiments were run without applying the suggested fix. A repetition of the Oshiwambo-English and German-English Experiments yielded the same results within the tolerance of the standard deviation. This is most likely the case, since the bug fix only modifies unsorted seed inputs, and the seeds used in my implementation are sorted by default._
- Make the following changes to the `_add_embeddings_internal` function of the `BytePairEmbeddings` class in `./flair/flair/embeddings/token.py`
  - For weighted embeddings: 
    ```python
        def _add_embeddings_internal(self, sentences: List[Sentence]) -> List[Sentence]:
        tokens = [token for sentence in sentences for token in sentence.tokens]

        word_indices: List[List[int]] = []
        index_weights: List[List[int]] = []
        for token in tokens:
            word = token.text if self.field is None else token.get_label(self.field).value

            if word.strip() == "":
                ids = [self.spm.vocab_size(), self.embedder.spm.vocab_size()]
                weights = []
            else:
                if self.do_preproc:
                    word = self._preprocess(word)
                ids = self.spm.EncodeAsIds(word.lower())
                weights = [len(sub_word.replace('▁', '')) for sub_word in self.spm.EncodeAsPieces(word.lower())]
            word_indices.append(ids)
            index_weights.append(weights)

        index_tensor = torch.tensor(word_indices, dtype=torch.long, device=self.device)
        embeddings = self.embedding(index_tensor)
        weighted_embeddings = []
        for token_embeddings, embedding_weights in zip(embeddings, index_weights):
            weighted_embedding = torch.zeros(token_embeddings[0].size())
            for embedding, weight in zip(token_embeddings, embedding_weights):
                weighted_embedding += weight * embedding
            weighted_embeddings.append(weighted_embedding/sum(embedding_weights))
        embeddings = torch.stack(weighted_embeddings, dim=0)
        if self.force_cpu:
            embeddings = embeddings.to(flair.device)

        for emb, token in zip(embeddings, tokens):
            token.set_embedding(self.name, emb)

        return sentences
    ```
  - For mean embeddings replace `embeddings = embeddings.reshape((-1, self.embedding_length))` with `embeddings = torch.mean(embeddings, dim=1)`
- Add corpus files to this directory names `corpus-LANG.txt`
- Add seed translations as a json dictionary with entries `"word": ["translation1", "translation2", ...]` to `translations-SRC-TRG.json`
- Set-up [Glove](https://github.com/stanfordnlp/GloVe) and specify the build location in `glove.sh` 
# Running Experiments

Make sure to set the source and target languages and the corpus type ('small' or 'extended') in the `constants.py` file.

## Setting up Embeddings
- Edit the tmp directory in `glove.sh`, `run_glove.sh` and `word_embedding_creation.sh` to the path of your preferred tmp directory. 
- Embedding Training:
  - BytePairEmbeddings: run the `byte_pair_embedding_creation.sh` script.
  - WordEmbeddings: run the `word_embedding_creation.sh` script 

## Running BLI
- Choose the correct embedding type in `graph_matching.py`
- Run `param_search.sh` with the desired parameters.
- The results are saved in `stats-CORPUSTYPE.txt` and the best dictionary is saved named with the best parameters.
- Alternatively, run `python run_goat_for_bli.py --corpus_type=extended --vocab_size=10000 --num_seeds=100 --end_proc=True `

## Isomorphism Metrics
- The Embedding files need to be saved in a word2vec format. Use the provided `convert_to_word2vec.py` script to convert the embeddings.
- The metrics can be computed using `python evs-python-3.py SRC.word2vec TRG.word2vec` and `python gh-python-3.py SRC.word2vec TRG.word2vec` for the EVS and GH metrics respectively.
