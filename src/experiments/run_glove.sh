# Change the tmp directory to where ever the glove.sh is set up to save the temp files. If this is not set up correctly
# It will cause problems when training embeddings for different parameters.
rm /tmp/breidina/*
source constants.py
glove.sh encoded-$SRC-$CORPUS_TYPE-$VOCAB_SIZE.txt embeddings-$SRC-$CORPUS_TYPE-$VOCAB_SIZE $EMBEDDING_DIMENSION
glove.sh encoded-$TRG-$CORPUS_TYPE-$VOCAB_SIZE.txt embeddings-$TRG-$CORPUS_TYPE-$VOCAB_SIZE $EMBEDDING_DIMENSION
