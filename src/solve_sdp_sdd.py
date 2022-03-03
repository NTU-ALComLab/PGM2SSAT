import os
import sys
from pathlib import Path
from pypsdd import Vtree, SddManager, PSddManager, SddNode
from pypsdd import Timer, DataSet, Inst, InstMap
from pypsdd import Prior, DirichletPrior, UniformSmoothing
from pypsdd import io


def main(argv):
    vtree_file = argv[1]
    sdd_file = argv[2]

    # read SDD
    vtree = Vtree.read(vtree_file)
    manager = SddManager(vtree)
    sdd = io.sdd_read(sdd_file, manager)

    pmanager = PSddManager(vtree)
    psdd = pmanager.copy_and_normalize_sdd(sdd, vtree)


if __name__ == "__main__":
    main(sys.argv)
