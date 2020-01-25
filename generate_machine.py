from machinedef import commands, NVECREG, NFLOATREG, command_system, command_system_hash
import os

def make_header(ofile):
    ofile.write(f"#define NVECREG {NVECREG}\n")
    ofile.write(f"#define NFLOATREG {NFLOATREG}\n")
    ofile.write("enum command{\n")
    for cmd in commands:
        comment = '' if cmd.enabled else '/*disabled*/'
        ofile.write(f"    cmd_{cmd.name},{comment}\n")
    ofile.write("};\n")
    ofile.write(f"const command cmd_max=static_cast<command>(cmd_{commands[-1].name}+1);\n")
    ofile.write("std::ostream &operator <<(std::ostream &os, command c);\n")
    ofile.write("argument_type get_argument_type(i8 command);\n")

    ofile.write("const char* command_system_hash();\n");

    
def make_cmd2str(ofile):
    ofile.write("std::ostream &operator <<(std::ostream &os, command c){\n")
    ofile.write("    switch(c){\n")
    for idx,cmd in enumerate(commands):
        ofile.write(f"    case cmd_{cmd.name}:\tos<<\"{cmd.name}\"; break;\n")
    ofile.write(f"    default: os<<\"badcmd\"<<(int)c;\n")
    ofile.write( "    }\n")
    ofile.write( "    return os;\n")
    ofile.write( "}\n")

def make_get_argument_type(ofile):
    ofile.write("""\
argument_type get_argument_type(i8 command)
{
    switch(command){
""")
    for cmd in commands:
        ofile.write(f"    case cmd_{cmd.name}: return arg_{cmd.argtype.value};\n")
    ofile.write("""\
    default: return arg_no;
    }
}
""")

def make_machine_step(ofile):
    ofile.write("""\
#define VEC_REGISTER (vec_registers[instr.arg_index])
#define FLOAT_REGISTER (float_registers[instr.arg_index])
void Machine::step()
{
  nsteps += 1;
  if(code.size() ==0) return;
  instruction &instr(code[cpr]);
  MTRACE("#"<<cpr<<" : "<<instr.cmd);
  switch(instr.cmd){
""")
    for cmd in commands:
        ofile.write(f"    case cmd_{cmd.name}:{{\n")
        if not cmd.enabled:
            ofile.write("    /*Command disabled*/\n")
        else:
            if cmd.condition is not None:
                ofile.write('    if ({}flag){{\n'.format('' if cmd.condition else '!'))
            ofile.write(cmd.cppcode)
            if "f" in cmd.changes:
                ofile.write('    MTRACE(" => FLAG="<<flag);\n')
            if 'va' in cmd.changes:
                ofile.write('    MTRACE(" => VACC="<<vec_accum);\n')
            if 'vr' in cmd.changes:
                ofile.write('    vec_registers_changed[instr.arg_index]=true;\n')
                ofile.write('    MTRACE(" => VREG["<<instr.arg_index<<"]="<<VEC_REGISTER);\n')
            if 'fa' in cmd.changes:
                ofile.write('    MTRACE(" => FACC="<<float_accum);\n')
            if 'fr' in cmd.changes:
                ofile.write('    MTRACE(" => FREG["<<instr.arg_index<<"]="<<FLOAT_REGISTER);\n')
            if 'j' in cmd.changes:
                ofile.write('    MTRACE(" => JMP to"<<cpr);\n')
            if cmd.condition is not None:
                ofile.write('    }\n')
        ofile.write(f"    }}break;\n")
    ofile.write("""\
    }
    if (++cpr == code.size()) cpr = 0;
}
#undef VEC_REGISTER
#undef FLOAT_REGISTER
""")

def make_cpp(ofile):
    ofile.write( "const char *command_system_hash(){\n"
                f'  return "{command_system_hash()}";\n'
                 "}\n")
    make_cmd2str(ofile)
    make_get_argument_type(ofile)
    make_machine_step(ofile)
import hashlib

def store_hash():
    h = command_system_hash()
    cache = "command_systems_cache"
    fpath = os.path.join(cache, f"{h}.txt")
    if os.path.exists(fpath):
        print(f"Cached file {fpath} already exists")
    else:
        os.makedirs(cache,exist_ok=True)
        with open(fpath, "w") as hf:
            hf.write(command_system())
    
import sys
if __name__=="__main__":

    with open("machinedef_hpp.inl","w") as header:
        make_header(header)
    with open("machinedef_cpp.inl","w") as cppfile:
        make_cpp(cppfile)
    store_hash()
