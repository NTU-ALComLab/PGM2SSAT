./timeout -t 3600 -m 16000000 ./bin/merlin -f $1 -o $1.merlin -q $1.map -e $1.evid -a bte -t MMAP 2>&1 | tee $1.merlin.log
