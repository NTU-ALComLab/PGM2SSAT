import os
import sys
import random

file_dir = sys.argv[2]
label = int(sys.argv[3])
num_vars = int(sys.argv[1])
num_state = 2
num_value = num_state**num_vars
filename = 'rand_n%d_s%d_%d.cpt' % (num_vars, num_state, label)


f = open(os.path.join(file_dir, filename), 'w')
f.write('CPT\n')
f.write('%d\n' % num_vars)
for i in range(num_vars):
    f.write('%d ' % (num_state))
f.write('\n')

f.write('%d\n' % num_value)
for i in range(num_value):
    f.write('%.2f\n' % (random.random()))
