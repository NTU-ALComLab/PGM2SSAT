import os
import sys

dirname = sys.argv[1]

for i in range(2, 22, 2):
    for j in range(1, 6):
        os.system('sh gen_cpt.sh %d %s %d' % (i, dirname, j))
