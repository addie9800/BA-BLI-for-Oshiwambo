# Change the tmp directory to where ever the glove.sh is set up to save the temp files. If this is not set up correctly
# It will cause problems when training embeddings for different parameters.
rm /tmp/breidina/*
source constants.py
glove.sh corpus-$SRC.txt embeddings-$SRC-test $EMBEDDING_DIMENSION
glove.sh corpus-$TRG.txt embeddings-$TRG-test $EMBEDDING_DIMENSION
