from collections import namedtuple
import hashlib

commands = []
Command=namedtuple('Command', 'name, argtype, cppcode, condition, changes, jumpdir, enabled, code'.split(', '))

Command.do_changes = lambda self, flag: self.enabled and (flag in self.changes)

CHANGEFLAGS = set("b fa va fr vr j".split())
def command(name, argtype, cppcode, condition=None, changes="", jumpdir=None, enabled=True):
    _changes=frozenset(changes.split())
    assert isinstance(argtype, ArgType)
    if not all((c in CHANGEFLAGS) for c in _changes):
        raise ValueError(f"Bad change flags: {changes}")
    commands.append(Command(name, argtype, cppcode, condition, _changes,
                            jumpdir, enabled, code=len(commands)))

def command_system():
    """Return definition of the command system as string"""
    return "["+",".join(f"Command({c.name!r},{c.argtype},{c.cppcode!r},{c.condition!r},{sorted(c.changes)!r},{c.jumpdir!r},{c.enabled!r},{c.code})" 
                     for c in commands) + "]"

def command_system_hash():
    """return string that hopefully uniquely identified used command system"""
    return hashlib.md5(command_system().encode("utf-8")).hexdigest()

#argument types. match the "argument_type enum"
from enum import Enum
class ArgType(Enum):
    NO = "no"
    FREG = "float_register"
    FVAL = "float_value"
    VREG = "vec_register"
    LABEL = "label"
    def __repr__(self): return str(self)

command('nop', ArgType.NO, "")
command('vload', ArgType.VREG, """\
    vec_accum = VEC_REGISTER;
""", changes="va")
command('vstore', ArgType.VREG, """\
    VEC_REGISTER = vec_accum;
""", changes="vr")
command('vrand', ArgType.NO, """\
    random_vec(vec_accum.x);
    vec_accum.evaluated = false;
""",changes="va",enabled=False)
command('vmerge', ArgType.VREG, """\
    vec_accum.x *= float_accum;
    vec_accum.x.add_scaled(1.0-float_accum, VEC_REGISTER.x) ;
    vec_accum.evaluated = false;
""",changes="va")
command('vswap', ArgType.VREG, """\
    std::swap(vec_accum, VEC_REGISTER);
""",changes="va vr")
command('vless', ArgType.VREG, """\
    evaluate(vec_accum);
    evaluate(VEC_REGISTER);
    flag = vec_accum.f < VEC_REGISTER.f;
""",changes="b")
command('fload', ArgType.FREG, """\
    float_accum = FLOAT_REGISTER;
""",changes="fa")
command('fload_value', ArgType.FVAL, """\
    float_accum = instr.arg_float;
""",changes="fa")
command('fstore', ArgType.FREG, """\
    FLOAT_REGISTER = float_accum;
""",changes="fr")
command('fadd', ArgType.FREG, """\
    float_accum += FLOAT_REGISTER;
""")
command('fadd_value', ArgType.FVAL, """\
    float_accum += instr.arg_float;
""",changes="fa")
command('fmul', ArgType.FREG, """\
    float_accum *= FLOAT_REGISTER;
""",changes="fa",enabled=False)
command('fmul_value', ArgType.FVAL, """\
    float_accum *= instr.arg_float;
""",changes="fa",enabled=False)
command('fswap', ArgType.FREG, """\
    std::swap(float_accum, FLOAT_REGISTER);
""",changes="fa fr")
command('fless', ArgType.FREG, """\
    flag = float_accum < FLOAT_REGISTER;
""", changes="b")
command('fless_value', ArgType.FVAL, """\
    flag = float_accum < instr.arg_float;
""",changes="b")

code_jump="   cpr = instr.arg_address;\n"
command('jump_up', ArgType.LABEL, code_jump, jumpdir="up",changes="j")
command('jump_down', ArgType.LABEL, code_jump, jumpdir="down",changes="j")
command('iftrue_up', ArgType.LABEL, code_jump, jumpdir="up", condition=True,changes="j")
command('iftrue_down', ArgType.LABEL, code_jump, jumpdir="down", condition=True,changes="j")
command('iffalse_up', ArgType.LABEL, code_jump, jumpdir="up", condition=False,changes="j")
command('iffalse_down', ArgType.LABEL, code_jump, jumpdir="down", condition=False,changes="j")

command('label', ArgType.LABEL, "")
command('trace', ArgType.NO, """\
    if (tracing){
      std::cout<<"====================================="<<std::endl;
      show(std::cout);
    }
""", enabled=False)

NVECREG = 16
NFLOATREG = 16

name2cmd = {cmd.name: cmd for cmd in commands}

