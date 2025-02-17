#! /usr/bin/env bash

# This script is modified from https://github.com/bheinzerling/bpemb/issues/5
set -eou pipefail

# set this to something else if you want to keep GloVe co-occurrence files permanently,
# say, to create embeddings of the same corpus with different dimensions
TMP=/tmp/breidina
mkdir -p $TMP
#
# need to set this
BUILDDIR=~/Dokumente/GloVe/build
#
# set this to something appropriate for your system
NUM_THREADS=24
#
# path of single plain text file containing the byte-pair encoded corpus
CORPUS=$1
# where the GloVe files should be saved
OUT=$2
# GloVe embedding dim
VECTOR_SIZE=$3
#
FNAME=$(echo $CORPUS | sed "s#/#_#g")
SAVE_FILE=$OUT.glove
VERBOSE=2
MEMORY=64.0
#
# we want embeddings for *all* BPE symbols
VOCAB_MIN_COUNT=0
#
MAX_ITER=50
WINDOW_SIZE=15
BINARY=0
X_MAX=10
#
#
# this part is probably not necessary unless you create lots of embeddings
VOCAB_FILE=$TMP/$FNAME.vocab.txt
COOCCURRENCE_FILE=$TMP/$FNAME.cooccurrence.bin
COOCCURRENCE_SHUF_FILE=$TMP/$FNAME.cooccurrence.shuf.bin
# random filenames for overflow and tempshuf files to prevent naming clashes
OVERFLOW=$TMP/${FNAME}.overflow_$(echo $RANDOM $RANDOM $RANDOM $RANDOM $RANDOM | md5sum | cut -c -8)
TEMPSHUF=$TMP/${FNAME}.tempshuf_$(echo $RANDOM $RANDOM $RANDOM $RANDOM $RANDOM | md5sum | cut -c -8)
# create vocab and cooccurrence files only once
if [ ! -f $VOCAB_FILE ]; then
	echo "$ $BUILDDIR/vocab_count -min-count $VOCAB_MIN_COUNT -verbose $VERBOSE < $CORPUS > $VOCAB_FILE"
	$BUILDDIR/vocab_count -min-count $VOCAB_MIN_COUNT -verbose $VERBOSE < $CORPUS > $VOCAB_FILE
fi 	
if [ ! -f $COOCCURRENCE_FILE ]; then
	echo "$ $BUILDDIR/cooccur -memory $MEMORY -vocab-file $VOCAB_FILE -verbose $VERBOSE -window-size $WINDOW_SIZE < $CORPUS > $COOCCURRENCE_FILE"
 	$BUILDDIR/cooccur -memory $MEMORY -vocab-file $VOCAB_FILE -verbose $VERBOSE -window-size $WINDOW_SIZE -overflow-file $OVERFLOW < $CORPUS > $COOCCURRENCE_FILE
	if [ -f $OVERFLOW ]; then
 		rm $OVERFLOW
	fi
fi
if [ ! -f $COOCCURRENCE_SHUF_FILE ]; then
	echo "$ $BUILDDIR/shuffle -memory $MEMORY -verbose $VERBOSE -temp-file $TEMPSHUF < $COOCCURRENCE_FILE > $COOCCURRENCE_SHUF_FILE"
	$BUILDDIR/shuffle -memory $MEMORY -verbose $VERBOSE -temp-file $TEMPSHUF < $COOCCURRENCE_FILE > $COOCCURRENCE_SHUF_FILE
	if [ -f $TEMPSHUF ]; then
		rm $TEMPSHUF
	fi
fi

# print the command we're running 
echo "$ $BUILDDIR/glove -save-file $SAVE_FILE -threads $NUM_THREADS -input-file $COOCCURRENCE_SHUF_FILE -x-max $X_MAX -iter $MAX_ITER -vector-size $VECTOR_SIZE -binary $BINARY -vocab-file $VOCAB_FILE -verbose $VERBOSE -write-header 1 -alpha 0.75 -eta 0.03"
# the actual command
# GloVe will cause a segmentation fault for some combinations of large vocabulary sizes and large vector sizes.
# In those cases, changing  alpha and eta slightly fixes the problem ‾\_(ツ)_/‾
$BUILDDIR/glove -save-file $SAVE_FILE -threads $NUM_THREADS -input-file $COOCCURRENCE_SHUF_FILE -x-max $X_MAX -iter $MAX_ITER -vector-size $VECTOR_SIZE -binary $BINARY -vocab-file $VOCAB_FILE -verbose $VERBOSE -write-header 1 -alpha 0.75 -eta 0.03
# delete the <unk> embedding, assumes that <unk> doesn't occur as part of some BPE symbol
sed -i "/<unk>/d" ${SAVE_FILE}.txt
#
