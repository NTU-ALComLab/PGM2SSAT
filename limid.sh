./timeout -t 3600 -m 16000000 ./bin/limid $1 2>&1 | grep -e MEU -e CPU -e Memory -e FINISHED  | tee $1.limid.log
