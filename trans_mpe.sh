#./timeout -t 300 python3 src/encode.py bn0 $1 
./timeout -t 1000 python3 src/encode.py -i $1 -n BN -q MPE -m val -p -c | tee $1.log
