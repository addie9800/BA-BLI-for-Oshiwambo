
#!/bin/bash

# Define the parameter search space
vocab_size_values=(10000 20000 50000)

# Loop through combinations of parameters
for vocab_size in "${vocab_size_values[@]}"; do
       		# Update constants.py with current parameter values
        	sed -i "s/^VOCAB_SIZE=.*/VOCAB_SIZE=$vocab_size/" constants.py
        	# Run your dependent script(s)
        	python embeddings.py
          run_glove.sh
          python align_vocab.py
done
