# PGM2SSAT
Stochastic Boolean Satisfiability (SSAT) encoding of Probabilistic Graphical Model (PGM) problems

1. Files:
 - src: source code
 - .sh files: the running scripts


2. PGMs to SSAT
To convert the network (.uai file) and the corresponding query file (.map and .evid for MAP, .sdp for SDP) into SSAT formula (.ssat file for DC-SSAT, .sdimacs file for erSSAT and ClauSSat), the commands are as follows:
- MAP: sh trans_map.sh ".uai file"
- SDP: sh trans_sdp.sh ".uai file"
- MEU: sh trand_id.sh ".uai file"


3. Solvers' scripts
(Please put the compiled binary file into bin/ directory)
- DC-SSAT: sh dcssat.sh ".ssat file"
- ClauSSat: sh claussat.sh ".sdimacs file"
- erSSAT: sh erssat.sh ".sdimacs file"
- bte: sh merlin_mmap.sh ".uai file"
- limid: sh limid.sh ".uai file"
- SDD: sh sdp2sdd.sh ".ssat file"


4. Solvers' links:
- ClauSSat: https://github.com/NTU-ALComLab/ClauSSat.git
- erSSAT: https://github.com/NTU-ALComLab/ssatABC.git
- Merlin: https://github.com/radum2275/merlin.git
- SDD: https://github.com/wannesm/PySDD.git
- limid: https://github.com/radum2275/limid.git
- ST-WMBMM: https://github.com/junkyul/gmid2-public.git


5. benchmarks:
MAP, SDP, MEU computations are in the benchmarks.
- .uai: Bayesian network or Influence diagram
- .map: The y variables in MAP
- .evid: The evidence in MAP
- .sdp: The query variables in SDP


6. Run benchmarks with multiple cores:

- python3 src/run_all.py "script.sh" "directory" "extension" "core number"

    For example, we convert all the uai files into SSAT in benchmarks/sdp/ with 8 cores:

- python3 src/run_all.py trans_sdp.sh benchmarks/sdp/ .uai 8



7. Experiment flow:
- bte, limid:
  - preprocess the networks with preprocess_"network".sh
  - Run the scripts with _prune.uai files
- DC-SSAT, erSSAT, ClauSSat:
    - Convert .uai files into .ssat or .sdimacs files
    - Run the scripts with SSAT files
- SDD:
    - Convert .uai files into .ssat files
    - Run the scripts with .ssat files