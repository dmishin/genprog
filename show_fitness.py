#!/usr/bin/env python
from machine import randomize, Machine, FunctionTable, command_system_hash
from genetic_optim import Fitness
import argparse
from utils import load_code
    
if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("codefile",
                        nargs='+',
                        help="Input code files, in JSON format")
    args = parser.parse_args()
    randomize()
    fitness = Fitness(maxsteps = 10000,
                      maxevals = 1000,
                      tol = 1e-5)
    func_index, expected_point = 0, (1.0,1.0)
    for fname in args.codefile:
        print(f"Code : {fname}")
        print(f"    Function index {func_index}")
        code = load_code(fname, check_hash=command_system_hash())
        print("    Fitness:", fitness(code, func_index, expected_point))
        
