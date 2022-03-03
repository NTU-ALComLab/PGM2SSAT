./timeout -t 3600 -m 16000000 ./bin/abc -c "ssat -c $1" 2>&1 | tee $1.sdimacs.log
