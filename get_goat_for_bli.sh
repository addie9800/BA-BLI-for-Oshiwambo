echo Getting GOAT for BLI
git clone https://github.com/kellymarchisio/goat-for-bli.git
echo Getting third party packages
chmod +x ./goat-for-bli/third_party/get_packages.sh
cd goat-for-bli/third_party
./get_packages.sh
cd ./goat/pkg
pip install .
echo -e "In case you missed it (message from GOAT for BLI): \n\n"
echo !!!! There is a bug in here that you need to manually correct !!!!
echo -e "\t Namely, after line 387 in third_party/goat/pkg/pkg/gmp/qap.py, you must add:"
echo -e "\t\t# Cannot assume partial_match is sorted"
echo -e "\t\tpartial_match = np.row_stack(sorted(partial_match, key=lambda x: x[0]))"
echo -e "\t  and the same after line 397 in third_party/goat/pkg/pkg/gmp/qapot.py"
echo Finally, remember to add /goat-for-bli/ as a source root directory