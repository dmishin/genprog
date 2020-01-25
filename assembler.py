import re
import os
import machinedef
codes = [c.name for c in machinedef.commands]#parseheader.commands[:-1]
code2index = {c.name:c.code for c in machinedef.commands}

def _codes_by_argtype(atype):
    return set(c.name for c in machinedef.commands if c.argtype==atype)
nop_codes = _codes_by_argtype(machinedef.ArgType.NO)
vregister_codes = _codes_by_argtype(machinedef.ArgType.VREG)
fregister_codes = _codes_by_argtype(machinedef.ArgType.FREG)
float_arg_codes = _codes_by_argtype(machinedef.ArgType.FVAL)
label_codes = _codes_by_argtype(machinedef.ArgType.LABEL)
def compile_code(source):
    """Compile asembly to executable bytecode"""
    compiled = []
    for line in source.split("\n"):
        #clean up the line
        line = line.split('#',1)[0].strip()
        #remove line number if present
        m = re.match(r"^\s*\d+\s*(.*)$", line)
        if m: line = m.group(1)
        if not line: continue
        parts = re.split(r"\s+", line)
        op = parts[0].lower()
        args = parts[1:]
        compiled.append(code2index[op])
        if op in nop_codes:
            compiled.append(0)
        else:
            if len(args) != 1:
                raise ValueError(f"One argument expected: {line}, {args}")
            arg = args[0]
            if op in vregister_codes or op in fregister_codes:
                compiled.append(int(arg))
            elif op in float_arg_codes:
                compiled.append(float2byte(float(arg)))
            elif op in label_codes:
                compiled.append(int(arg))
            else:
                raise ValueError("Bad code"+line)
    return bytes(compiled)

def float2byte(arg):
    return int(round(float(arg)*32.0))&255

if __name__=="__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser()
    parser.add_argument("source",
                        help="Input dource code file, in text format")
    parser.add_argument("-o", "--output", help="Output json file (default is name.json)")
    args = parser.parse_args()
    if args.output:
        out = args.output
    else:
        out = os.path.splitext(args.source)[0] + ".json"

    with open(args.source, "r")  as hin:
        bytecode = compile_code(hin.read())
        
    with open(out, "w") as hout:
        json.dump({'hexcode': bytecode.hex(),
                   'command_system_hash': machinedef.command_system_hash(),
                   'description': f"Compiled source {args.source}"
        }, hout)
        hout.write("\n")
