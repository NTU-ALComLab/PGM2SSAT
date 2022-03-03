import os
import sys
import glob
import csv


def parse_cachet_log(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    runtime = None
    prob = None
    for line in lines:
        if line[:14] == 'Total Run Time':
            runtime = float(line.strip().split()[-1])
        elif line[:22] == 'Satisfying probability':
            prob = float(line.strip().split()[-1])

    return runtime, prob


def parse_pe_transform_log(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    if len(lines) < 18:
        return None, None, None

    scale = int(lines[18].strip().split()[-1])
    summary = lines[19].strip().split(' = ')[-1].replace('(', '').replace(')', '').split(',')
    num_vars = int(summary[0])
    num_cls = int(summary[1])

    return scale, num_vars, num_cls


def parse_sdp_transform_log(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    if len(lines) < 16:
        return None, None, None, None, None, None, None, None

    if lines[2][:4] != 'Find':
        return None, None, None, None, None, None, None, None

    if lines[7][:9] == 'Traceback':
        return None, None, None, None, None, None, None, 'no stop'

    if lines[14][:9] == 'Traceback':
        return None, None, None, None, None, None, None, None

    scale = int(lines[15].strip().split()[-1])
    summary = lines[16].strip().split(' = ')[-1].replace('(', '').replace(')', '').split(',')
    num_vars = int(summary[0])
    num_cls = int(summary[1])

    num_entry = int(lines[3].strip().split()[-1])
    num_pruned = int(lines[5].strip().split()[-1])
    num_d_pruned = int(lines[6].strip().split()[-1])
    useful = (num_pruned != num_d_pruned)
    # num_cc = int(lines[7].strip().split()[-1])
    num_cc = 0

    transtime = None
    memory = None
    for line in lines:
        if line[:8] == 'FINISHED':
            pars = line.strip().split()
            transtime = float(pars[2])
            memory = int(pars[6])

    return scale, num_vars, num_cls, transtime, memory, useful, num_cc, num_entry


def parse_map_transform_log(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()
    # print(filename)
    if len(lines) < 14:
        return None, None, None, None, None

    if lines[2][:4] != 'Find':
        return None, None, None, None, None

    if lines[13][:9] == 'Traceback':
        return None, None, None, None, None

    scale = int(lines[13].strip().split()[-1])
    summary = lines[14].strip().split(' = ')[-1].replace('(', '').replace(')', '').split(',')
    num_vars = int(summary[0])
    num_cls = int(summary[1])

    transtime = None
    memory = None
    for line in lines:
        if line[:8] == 'FINISHED':
            pars = line.strip().split()
            transtime = float(pars[2])
            memory = int(pars[6])

    return scale, num_vars, num_cls, transtime, memory


def parse_id_transform_log(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    if len(lines) < 11:
        return None, None, None, None, None, None, None, None, None, None

    if lines[5][:9] == 'Traceback':
        return None, None, None, None, None, None, None, None, None, None

    # util = lines[8].strip().split(' = ')[-1].replace('(', '').replace(')', '').split(',')
    # max_u = float(util[0])
    # min_u = float(util[1])
    util = lines[8].strip().split(', ')
    util_scale = float(util[0].split()[-1])
    util_shift = float(util[1].split()[-1])
    scale = int(lines[7].strip().split()[-1])
    scale2 = int(lines[11].strip().split()[-1])
    summary = lines[12].strip().split(' = ')[-1].replace('(', '').replace(')', '').split(',')
    num_vars = int(summary[0])
    num_cls = int(summary[1])
    level_info = lines[13].strip().split(' = ')[-1].replace('(', '').replace(')', '').split(',')
    num_level = int(level_info[0])
    per_level = [int(l) for l in level_info[1].replace('[', '').replace(']', '').split(',')]

    transtime = None
    memory = None
    for line in lines:
        if line[:8] == 'FINISHED':
            pars = line.strip().split()
            transtime = float(pars[2])
            memory = int(pars[6])

    return util_scale, util_shift, scale, scale2, num_vars, num_cls, num_level, per_level, transtime, memory


def parse_cpt_transform_log(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()
    # print(filename)
    if len(lines) < 13:
        return None, None, None, None, None

    if lines[11][:9] == 'Traceback':
        return None, None, None, None, None

    scale = int(lines[12].strip().split()[-1])
    summary = lines[13].strip().split(' = ')[-1].replace('(', '').replace(')', '').split(',')
    num_vars = int(summary[0])
    num_cls = int(summary[1])

    transtime = None
    memory = None
    for line in lines:
        if line[:8] == 'FINISHED':
            pars = line.strip().split()
            transtime = float(pars[2])
            memory = int(pars[6])

    return scale, num_vars, num_cls, transtime, memory


def parse_ssat_log(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    runtime = None
    memory = None
    prob = None

    for line in lines:
        if line[:14] == '   total time:':
            pars = line.strip().split()
            runtime = float(pars[-1])

        if line[:7] == 'Pr[SAT]':
            pars = line.strip().split()
            prob = float(pars[-1])

        if line[:3] == 'MEM' and runtime is None:
            pars = line.strip().split()
            runtime = 'MO'
            memory = int(pars[6])
        if line[:7] == 'TIMEOUT' and runtime is None:
            pars = line.strip().split()
            runtime = 'TO'
            memory = int(pars[6])
        if line[:8] == 'FINISHED':
            pars = line.strip().split()
            memory = int(pars[6])

    return runtime, memory, prob


def parse_samiam_log(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    sdp = None
    runtime = None
    memory = None

    for line in lines:
        if line[:4] == 'SDP:':
            pars = line.strip().split()
            sdp = float(pars[-1])

        if line[:8] == 'FINISHED':
            pars = line.strip().split()
            runtime = float(pars[2])
            memory = int(pars[6])

        if line[:3] == 'MEM' and runtime is None:
            pars = line.strip().split()
            runtime = 'MO'
            memory = int(pars[6])

        if line[:7] == 'TIMEOUT' and runtime is None:
            pars = line.strip().split()
            runtime = 'TO'
            memory = int(pars[6])

    return sdp, runtime, memory


def parse_merlin_mmap_log(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    prob = None
    runtime = None
    memory = None

    for i, line in enumerate(lines):
        if line[:4] == 'MMAP':
            prob = lines[i+1].strip()

        if line[:8] == 'FINISHED':
            pars = line.strip().split()
            runtime = float(pars[2])
            memory = int(pars[6])
        if line[:3] == 'MEM' and runtime is None:
            pars = line.strip().split()
            runtime = 'MO'
            memory = int(pars[6])
        if line[:7] == 'TIMEOUT' and runtime is None:
            pars = line.strip().split()
            runtime = 'TO'
            memory = int(pars[6])

    return prob, runtime, memory


def parse_limid_log(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    meu = None
    runtime = None
    memory = None

    for line in lines:
        if line[:3] == 'MEU':
            pars = line.strip().split()
            meu = float(pars[-1])

        if line[:8] == 'FINISHED':
            pars = line.strip().split()
            runtime = float(pars[2])
            memory = int(pars[6])

        if line[:3] == 'MEM' and runtime is None:
            pars = line.strip().split()
            runtime = 'MO'
            memory = int(pars[6])

        if line[:7] == 'TIMEOUT' and runtime is None:
            pars = line.strip().split()
            runtime = 'TO'
            memory = int(pars[6])

    return meu, runtime, memory


def parse_sdd_log(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    runtime = None
    memory = None

    finished = False
    flag = False
    for line in lines:
        if line[:8] == 'Read CNF':
            flag = True
        if flag and line[:4] == 'Save':
            finished = True
        if line[:8] == 'FINISHED':
            pars = line.strip().split()
            runtime = float(pars[2])
            memory = int(pars[6])

        if line[:3] == 'MEM' and runtime is None:
            pars = line.strip().split()
            runtime = 'MO'
            memory = int(pars[6])

        if line[:7] == 'TIMEOUT' and runtime is None:
            pars = line.strip().split()
            runtime = 'TO'
            memory = int(pars[6])

    return finished, runtime, memory


def parse_simp_log(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    num_vars = 0
    num_cls = 0
    scale = 1
    for line in lines:
        if line[:6] == 'Result':
            pars = line.strip().split()
            num_vars = int(pars[3])
            num_cls = int(pars[5])
        if line[:5] == 'Scale':
            scale = float(line.strip().split()[-1])
            break
        if line[:13] == 'UNSATISFIABLE':
            scale = 'unsat'
            break

    return num_vars, num_cls, scale


def parse_ssat_lit(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    num_vars = int(lines[0].strip())
    num_cls = int(lines[1].strip())
    num_lits = 0
    for i in range(num_vars+2, num_vars+num_cls+2):
        pars = lines[i].strip().split(' ')
        num_lits += len(pars) - 1

    return num_lits,


def parse_ssatabc_log(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    runtime = None
    memory = None
    prob = None

    for line in lines:
        if line[:8] == '  > Time':
            pars = line.strip().split()
            runtime = float(pars[-2])

        if line[:26] == '  > Satisfying probability':
            pars = line.strip().split()
            prob = float(pars[-1])

        if line[:3] == 'MEM':
            pars = line.strip().split()
            memory = int(pars[6])
            runtime = 'MO'

        if line[:7] == 'TIMEOUT':
            pars = line.strip().split()
            memory = int(pars[6])
            runtime = 'TO'

        if line[:8] == 'FINISHED':
            pars = line.strip().split()
            memory = int(pars[6])

    return runtime, memory, prob


def parse_claussat_log(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    ub = None
    lb = None
    runtime = None
    memory = None

    for i, line in enumerate(lines):
        if line[:15] == '  > Upper bound':
            ub = float(line.strip().split()[-1])
        if line[:15] == '  > Lower bound':
            lb = float(line.strip().split()[-1])
        if line[:23] == '  > Total time consumed':
            runtime = float(line.strip().split()[-1])
        if line[:8] == 'FINISHED':
            pars = line.strip().split()
            # runtime = float(pars[2])
            memory = int(pars[6])

        if line[:3] == 'MEM':
            pars = line.strip().split()
            memory = int(pars[6])
            runtime = 'MO'

        if line[:7] == 'TIMEOUT':
            pars = line.strip().split()
            memory = int(pars[6])
            runtime = 'TO'

    return runtime, memory, ub, lb


def parse_st_log(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    ub = None
    runtime = None
    memory = None

    for i, line in enumerate(lines):
        if line[:2] == 'ub':
            ub = float(line.strip().split()[-1])

        if line[:8] == 'FINISHED':
            pars = line.strip().split()
            runtime = float(pars[2])
            memory = int(pars[6])

        if line[:3] == 'MEM':
            pars = line.strip().split()
            runtime = 'MO'
            memory = int(pars[6])

        if line[:7] == 'TIMEOUT':
            pars = line.strip().split()
            runtime = 'TO'
            memory = int(pars[6])

    return runtime, memory, ub


def parse_sharpssat_log(filename):
    f = open(filename, 'r')
    lines = f.readlines()
    f.close()

    prob = None
    runtime = None
    memory = None

    for i, line in enumerate(lines):
        if line[:24] == '# satisfying probability':
            prob = float(line.strip().split()[-1])
        if line[:8] == 'FINISHED':
            pars = line.strip().split()
            runtime = float(pars[2])
            memory = int(pars[6])

        if line[:3] == 'MEM':
            pars = line.strip().split()
            memory = int(pars[6])
            runtime = 'MO'

        if line[:7] == 'TIMEOUT':
            pars = line.strip().split()
            memory = int(pars[6])
            runtime = 'TO'

    return runtime, memory, prob
