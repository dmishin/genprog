#!/usr/bin/env python
import re
import machinedef

def byte2float(b):
    if b > 127:
        b = b-256
    return b/32.0

def decompile_instruction(opcode, arg):
    opcode =int(opcode)
    arg = int(arg)
    #command = codes[opcode % len(codes)]
    command = machinedef.commands[opcode % len(machinedef.commands)]
    if not command.enabled: return ""
    if command.argtype == machinedef.ArgType.NO:
        code = command.name
    else:
        if command.argtype == machinedef.ArgType.VREG:
            sarg = arg%machinedef.NVECREG
        elif command.argtype == machinedef.ArgType.FREG:
            sarg = arg%machinedef.NFLOATREG
        elif command.argtype == machinedef.ArgType.FVAL:
            sarg = byte2float(arg)
        elif command.argtype == machinedef.ArgType.LABEL:
            sarg = arg
        else:
            raise ValueError("Bad command code: {}".format(opcode))
        code = "{} {}".format(command.name, sarg)
    if not command.enabled:
        code = "#" + code
    return code

def decompile(bincode):    
    return "\n".join(filter(bool, (decompile_instruction(oc, arg)
                            for oc, arg in zip(bincode[::2],bincode[1::2]))))
def map_jumps(code):
    from machine import Machine, command_system_hash
    assert command_system_hash() == machinedef.command_system_hash()
    m = Machine()
    m.load_code(code)
    jmap = {}
    for i in range(0, len(code)-1, 2):
        target = m.get_jump_index(i//2)*2
        if target == -2: continue
        if target != i:
            #successfully found jump target
            jmap[i] = target
        else:
            #jump to self - special case. move to the next instruction
            jmap[i] = (target + 2)%len(code)
    return jmap

def listing(bincode, ofile, show_dead_code=True):
    jumpmap = map_jumps(bincode)
    if show_dead_code:
        live_code_map = map_live_code(bincode)
    for i in range(0, len(bincode)-1,2):
        line = decompile_instruction(bincode[i],bincode[i+1])
        if i in jumpmap:
            line = line + "#-->{}".format(jumpmap[i])
        if show_dead_code and not live_code_map[i//2]:
            line = line + "#DEAD"
        ofile.write("{}\t{}\n".format(i,line))

def map_live_code(bincode, func_index=0, steps=10000, attempts = 10):
    """Run the program several times to get live code map"""
    from machine import Machine, command_system_hash, FunctionTable
    assert command_system_hash() == machinedef.command_system_hash()
    m = Machine()
    m.load_code(bincode)
    m.set_trace_live_code(True)
    m.set_function(FunctionTable(func_index))
    for i in range(attempts):
        if i != 0: m.reset()
        m.steps(steps)
    #now map is ready
    return [m.is_instruction_live(i) for i in range(len(bincode)//2)]
        
if __name__=="__main__":
    from utils import load_code
    import argparse
    import sys
    
    parser = argparse.ArgumentParser()
    parser.add_argument("codefile",
                        help="Input code file, in JSON format")
    parser.add_argument("-o", "--output", help="Save listing as (default is stdout)")
    
    args = parser.parse_args()
        
    bincode = load_code(args.codefile, check_hash=machinedef.command_system_hash())

    if args.output:
        with open(args.output, "w") as hout:
            listing(bincode, hout)
    else:
        listing(bincode, sys.stdout)
                
