./timeout -t 3600 -m 16000000 python3 src/sdp_ssat2sdd.py $1 2>&1 | tee $1.sdd.log
