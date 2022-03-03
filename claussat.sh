./timeout -t 3600 -m 16000000 ./bin/claussat -uwsc $1 2>&1 | tee $1.claussat.log
