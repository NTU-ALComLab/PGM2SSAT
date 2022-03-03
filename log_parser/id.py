import os
import sys
import glob
import csv

from parselog import *


def main(argv):
    dirname = argv[1]
    outfile = os.path.join(dirname, 'log.csv')

    uai_files = glob.glob(os.path.join(dirname, '*.limid.log'))
    ssat_files = glob.glob(os.path.join(dirname, '*.ssat-heu.log'))
    limid_files = glob.glob(os.path.join(dirname, '*.limid.log'))
    claussat_files = glob.glob(os.path.join(dirname, '*.claussat.log'))
    st_wmbmm_files = glob.glob(os.path.join(dirname, '*.st_wmbmm_tw.log'))
    sharpssat_files = glob.glob(os.path.join(dirname, '*.sharpssat.log'))

    summary = {}

    '''
    Transform log
    '''
    for filename in uai_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting summary:', name)
        if '_prune' in name:
            continue
        summary[name] = [None]*26
        summary[name][:10] = list(parse_id_transform_log(filename))

    '''
    DCSSAT Runtime log
    '''
    for filename in ssat_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting answer:', name)
        if '_prune' in name:
            continue
        summary[name][10:13] = list(parse_ssat_log(filename))

    '''
    limid Runtime log
    '''
    for filename in limid_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0].replace('_prune', '')
        # print('Collecting answer:', name)
        summary[name][13:16] = list(parse_limid_log(filename))

    '''
    ClauSSat Runtime log
    '''
    for filename in claussat_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting answer:', name)
        if '_prune' in name:
            continue
        summary[name][16:20] = list(parse_claussat_log(filename))

    for filename in st_wmbmm_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0].replace('_prune', '')
        # print('Collecting answer:', name)
        summary[name][20:23] = list(parse_st_log(filename))

    for filename in sharpssat_files:
        head, tail = os.path.split(filename)
        name, ext = os.path.splitext(tail)
        name = name.split('.')[0]
        # print('Collecting answer:', name)
        summary[name][23:] = list(parse_sharpssat_log(filename))

    '''
    Summary
    '''
    with open(outfile, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Name', 'U scale', 'U shift', 'Scale', 'Scale2', 'Prob', '#v', '#cls', '#level', 'Trans Time',
                         'DCSSAT Time', 'DCSSAT Mem', 'MEU', 'Limid Time', 'Limid Mem',
                         'Claussat Time', 'Claussat Mem', 'Claussat ub', 'Claussat lb', 'st_time', 'st_mem', 'st_ub', 'sharp time', 'sharp mem', 'sharp prob'])
        keys = list(summary.keys())
        # keys.sort(key=lambda s: int(s.split('_')[-1]))
        keys.sort()
        for name in keys:
            max_u, min_u, scale, scale2, num_vars, num_cls, num_level, per_level, transtime, transmem, runtime, mem, prob, meu, limid_time, limid_mem, clau_time, clau_mem, clau_ub, clau_lb, st_time, st_mem, st_ub, sharp_time, sharp_mem, sharp_prob = summary[
                name]
            writer.writerow([name, max_u, min_u, scale, scale2, prob, num_vars, num_cls, num_level,
                             transtime, runtime, mem, meu, limid_time, limid_mem,
                             clau_time, clau_mem, clau_ub, clau_lb, st_time, st_mem, st_ub, sharp_time, sharp_mem, sharp_prob])


if __name__ == "__main__":
    main(sys.argv)
