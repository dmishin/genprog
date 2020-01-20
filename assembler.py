import re
#import parseheader
import machinedef
codes = [c.name for c in machinedef.commands]#parseheader.commands[:-1]
code2index = {code:idx for idx, code in enumerate(codes)}

def _codes_by_argtype(atype):
    return set(c.name for c in machinedef.commands if c.argtype==atype)
nop_codes = _codes_by_argtype(machinedef.NO)
vregister_codes = _codes_by_argtype(machinedef.VREG)
fregister_codes = _codes_by_argtype(machinedef.FREG)
float_arg_codes = _codes_by_argtype(machinedef.FVAL)
label_codes = _codes_by_argtype(machinedef.LABEL)


def compile_code(source):
    """Compile asembly to executable bytecode"""
    compiled = []
    
    for line in source.split("\n"):
        line = line.split('#',1)[0].strip()
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

def byte2float(b):
    if b > 127:
        b = b-256
    return b/32.0

if __name__=="__main__":
    bytecode = compile_code("""
################################
#sortarray of first 3 vectors
################################
#start sorting
label 30

# v0 < v1?
vload 0
vless 1
iftrue_down 30 #label 10
#swap v0 <-> v1
vswap 1
label 10
vstore 0    
label 30
""")
    print(bytecode)
