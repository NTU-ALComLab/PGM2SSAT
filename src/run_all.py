import sys
import os
import glob
import multiprocessing as mp

# want = '*.wcnf'


def run(script, filename):
    # cmd = 'runexec --keep-system-config --output %s.log sh %s %s >> %s.log' % (
    #     filename, script, filename, filename)
    cmd = 'sh %s %s' % (script, filename)
    os.system(cmd)


if __name__ == "__main__":
    # arguments
    script = sys.argv[1]
    dir_name = sys.argv[2]
    want = '*' + sys.argv[3]
    num_cores = 4
    if len(sys.argv) == 5:
        num_cores = int(sys.argv[4])

    # files
    p = os.path.join(dir_name, '**', want)
    filenames = glob.glob(p, recursive=True)
    args = [(script, file) for file in filenames]

    print('Use', num_cores, 'cores')
    pool = mp.Pool(num_cores)
    pool.starmap(run, args)
    # pool.starmap_async(run, args)
