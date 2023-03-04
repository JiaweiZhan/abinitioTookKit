# This file is used to cluster material based on criteria:
# 1. location to three closet atoms
# 2. density
# 3. potentially can use segmentation method from CV 
#   (Maximum Minimal Cut based on similarities between pixels)
from mpi4py import MPI
import argparse
from functools import partial
import signal
import pickle
from tqdm import tqdm
import numpy as np
import shutil, os, sys
from 

from abinitioToolKit import qbox_io, qe_io
from abinitioToolKit import utils

comm = MPI.COMM_WORLD

if __name__ == "__main__":
    signal.signal(signal.SIGINT, partial(utils.handler, comm))

    rank = comm.Get_rank()
    size = comm.Get_size()
    if rank == 0:
        utils.time_now()

    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--abinitio", type=str,
            help="abinitio software: qe/qbox. Default: qbox")
    parser.add_argument("-s", "--saveFileFolder", type=str,
            help="*.save folder generated by QE or the folder that store qbox output. Default: ../")
    parser.add_argument("-k", "--kpointIndex", type=int,
            help="kpoint index. Default: 1")
    parser.add_argument("-b", "--bandIndex", type=int,
            help="band index. Default: 1")
    args = parser.parse_args()

    if not args.abinitio:
        args.abinitio = "qbox"
    if not args.saveFileFolder:
        args.saveFileFolder = "../" 
    if not args.kpointIndex:
        args.kpointIndex = 1 
    if not args.bandIndex:
        args.bandIndex = 1 

    conf_tab = {"software": args.abinitio,
                "saveFileFolder": args.saveFileFolder,
                "band index": args.bandIndex,
                "kpoint index": args.kpointIndex,
                "MPI size": comm.Get_size()}
    utils.print_conf(conf_tab)

    # ------------------------------------------- read and store wfc --------------------------------------------
    
    abinitioRead = None
    if args.abinitio.lower() == "qbox":
        abinitioRead = qbox_io.QBOXRead(comm)
    elif args.abinitio.lower() == "qe":
        abinitioRead = qe_io.QERead(comm)

    storeFolder = './wfc/'

    comm.Barrier()
    isExist = os.path.exists(storeFolder)
    if not isExist:
        if rank == 0:
            print(f"store wfc from {storeFolder}")
        abinitioRead.read(args.saveFileFolder, storeFolder=storeFolder)
    else:
        if rank == 0:
            print(f"read stored wfc from {storeFolder}")
     
    # --------------------------------------- compute IPR by states----------------------------------------
    
    # comm.Barrier()
    with open(storeFolder + '/info.pickle', 'rb') as handle:
        info_data = pickle.load(handle)

    npv = info_data['npv']
    fftw = info_data['fftw']
    nbnd = info_data['nbnd']
    nspin = info_data['nspin']
    fileNameList = info_data['wfc_file']

    # TODO: 1. Qbox has no k point; 2. qe has no different nbnd

    for ispin in range(nspin):
        fileName = fileNameList[ispin][args.kpointIndex - 1, args.bandIndex - 1]
        wfc = np.load(fileName)
        fileName = str(ispin + 1) + "_" + str(args.kpointIndex).zfill(3) + "_" + str(args.bandIndex).zfill(5) + ".dat"
        utils.visualize_func(np.absolute(wfc) ** 2, zoom_factor=0.5, fileName=fileName)
        if rank == 0:
            print(f"output func in {fileName}")
    comm.Barrier()
    if rank == 0:
        shutil.rmtree(storeFolder)
