from collections import namedtuple
commands = []
Command=namedtuple('Command', 'name, argtype, cppcode, condition, changes, jumpdir, enabled, code'.split(', '))

Command.do_changes = lambda self, flag: self.enabled and (flag in self.changes)

CHANGEFLAGS = set("b fa va fr vr j".split())
def command(name, argtype, cppcode, condition=None, changes="", jumpdir=None, enabled=True):
    _changes=frozenset(changes.split())
    if not all((c in CHANGEFLAGS) for c in _changes):
        raise ValueError(f"Bad change flags: {changes}")
    commands.append(Command(name, argtype, cppcode, condition, _changes,
                            jumpdir, enabled, code=len(commands)))

#argument types. match the "argument_type enum"
NO = "no"
FREG = "float_register"
FVAL = "float_value"
VREG = "vec_register"
LABEL = "label"

command('nop', NO, "")
command('vload', VREG, """\
    vec_accum = VEC_REGISTER;
""", changes="va")
command('vstore', VREG, """\
    VEC_REGISTER = vec_accum;
""", changes="vr")
command('vrand', NO, """\
    random_vec(vec_accum.x);
    vec_accum.evaluated = false;
""",changes="va",enabled=False)
command('vmerge', VREG, """\
    vec_accum.x *= float_accum;
    vec_accum.x.add_scaled(1.0-float_accum, VEC_REGISTER.x) ;
    vec_accum.evaluated = false;
""",changes="va")
command('vswap', VREG, """\
    std::swap(vec_accum, VEC_REGISTER);
""",changes="va vr")
command('vless', VREG, """\
    evaluate(vec_accum);
    evaluate(VEC_REGISTER);
    flag = vec_accum.f < VEC_REGISTER.f;
""",changes="b")
command('fload', FREG, """\
    float_accum = FLOAT_REGISTER;
""",changes="fa")
command('fload_value', FVAL, """\
    float_accum = instr.arg_float;
""",changes="fa")
command('fstore', FREG, """\
    FLOAT_REGISTER = float_accum;
""",changes="fr")
command('fadd', FREG, """\
    float_accum += FLOAT_REGISTER;
""")
command('fadd_value', FVAL, """\
    float_accum += instr.arg_float;
""",changes="fa")
command('fmul', FREG, """\
    float_accum *= FLOAT_REGISTER;
""",changes="fa",enabled=False)
command('fmul_value', FVAL, """\
    float_accum *= instr.arg_float;
""",changes="fa",enabled=False)
command('fswap', FREG, """\
    std::swap(float_accum, FLOAT_REGISTER);
""",changes="fa fr")
command('fless', FREG, """\
    flag = float_accum < FLOAT_REGISTER;
""", changes="b")
command('fless_value', FVAL, """\
    flag = float_accum < instr.arg_float;
""",changes="b")

code_jump="   cpr = instr.arg_address;\n"
command('jump_up', LABEL, code_jump, jumpdir="up",changes="j")
command('jump_down', LABEL, code_jump, jumpdir="down",changes="j")
command('iftrue_up', LABEL, code_jump, jumpdir="up", condition=True,changes="j")
command('iftrue_down', LABEL, code_jump, jumpdir="down", condition=True,changes="j")
command('iffalse_up', LABEL, code_jump, jumpdir="up", condition=False,changes="j")
command('iffalse_down', LABEL, code_jump, jumpdir="down", condition=False,changes="j")
del code_jump

command('label', LABEL, "")
command('trace', NO, """\
    if (tracing){
      std::cout<<"====================================="<<std::endl;
      show(std::cout);
    }
""", enabled=False)

NVECREG = 16
NFLOATREG = 16

name2cmd = {cmd.name: cmd for cmd in commands}

