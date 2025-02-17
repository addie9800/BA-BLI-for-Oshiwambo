#!/bin/bash

# Define the parameter search space
# Change corpus_type to 'small' or 'extended' to run on the small or large corpus
# Make sure to set the languages in constants.py
vocab_size_values=(10000 20000 50000)
num_seeds_values=(50 75 100)
end_proc_values=('True' 'False')

# Loop through combinations of parameters
for vocab_size in "${vocab_size_values[@]}"; do
  for num_seeds in "${num_seeds_values[@]}"; do
    for end_proc in "${end_proc_values[@]}"; do
        python run_goat_for_bli.py --vocab_size $vocab_size --num_seeds $num_seeds --end_proc $end_proc --corpus_type 'small'
    done
  done
done

