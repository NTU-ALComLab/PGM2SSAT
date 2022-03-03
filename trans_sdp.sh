#./timeout -t 300 python3 src/encode.py bn0 $1
./timeout -t 1000 python3 src/encode.py -i $1 -n BN -q SDP -m val -o esp -p -cc 2>&1 | tee $1.log
