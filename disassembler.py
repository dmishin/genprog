import re
#import parseheader
from collections import defaultdict
from collections import namedtuple
import tempfile
import machinedef

def float2byte(arg):
    return int(round(float(arg)*32.0))&255

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
    if command.argtype == machinedef.NO:
        code = command.name
    else:
        if command.argtype == machinedef.VREG:
            sarg = arg%machinedef.NVECREG
        elif command.argtype == machinedef.FREG:
            sarg = arg%machinedef.NFLOATREG
        elif command.argtype == machinedef.FVAL:
            sarg = byte2float(arg)
        elif command.argtype == machinedef.LABEL:
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

def _map_jumps(code):
    jmap = {}
    for i in range(0, len(code)-1, 2):
        instr = code[i] % len(machinedef.commands)
        command = machinedef.commands[instr]
        arg = code[i+1]
        if command.jumpdir=="up":
            direction = -1
        elif command.jumpdir=="down":
            direction =  1
        else:
            continue
        target = _find_label(code, i, arg, direction);
        if target != i:
            #successfully found jump target
            jmap[i] = target
        else:
            #jump to self - special case. move to the next instruction
            jmap[i] = (target + 2)%len(code)
    return jmap

cmd_label = machinedef.name2cmd['label'].code
def _find_label(code, start, label, direction):
    codesize = (len(code)//2)*2
    i=start
    best_i = start
    best_dist = 1000
    while True:
        i = (i+direction*2)%codesize
        if i==start: break
        if code[i] % len(machinedef.commands) != cmd_label: continue
        dist = _label_dist(label, code[i+1])
        if dist < best_dist:
            best_dist = dist
            best_i = i
        if best_dist == 0:
            break
    return best_i

def _label_dist(a, b):
    diff = a ^ b;
    d = 0;
    while diff:
        d += diff % 2
        diff /= 2
    return d

class BaseBlock():
    def __init__(self, name, next):
        self.name = name
        self.next = next
class StartBlock(BaseBlock):
    pass
class Block(BaseBlock):
    def __init__(self, name, lines, next):
        BaseBlock.__init__(self, name, next)
        self.lines = lines
        self.instructions = []
    def append(self, c):
        self.lines.extend(c.lines)
        self.instructions.extend(c.instructions)
    def __str__(self):
        return self.name+":["+";".join(self.lines)+"]->"+self.next
class CondOp(BaseBlock):
    def __init__(self, name, iftrue, next, jump):
        BaseBlock.__init__(self, name, next)
        self.iftrue=iftrue
        self.jump = jump
    def __str__(self):
        return "{}:[if {}: ->{} else: ->{}]".format(self.name, self.iftrue, self.jump, self.next)
    
        
def parse_structure(code, optimize=True, show_address=False):
    """Decompile code and show its structure in graphwiz"""
    jumpmap = _map_jumps(code)

    label = machinedef.name2cmd['label'].code
    uncond_jumps = tuple( c.code for c in machinedef.commands
                          if c.condition is None and c.jumpdir)
    true_jumps = tuple( c.code for c in machinedef.commands
                        if c.condition is True and c.jumpdir)
    false_jumps = tuple( c.code for c in machinedef.commands
                         if c.condition is False and c.jumpdir)

    separators = set((label,)+uncond_jumps+true_jumps+false_jumps)

    #split code in blocks
    #blocks are delimited by jump and label instructions
    #
    blocks = {} #name -> block
    def blockname(addr):
        return "block{}".format(addr)
    def store(block):
        blocks[block.name]=block
        return block
    def new_block(at):
        return store(Block(blockname(at), [], blockname(0)))
    def new_condition(at, iftrue, jumpto):
        return store(CondOp(blockname(at), iftrue, next=blockname(0), jump=blockname(jumpto)))
    start = store(StartBlock("start",None))    

    prev_block = start
    cur_block = None
    
    for i in range(0,len(code)-1,2):
        if cur_block is None:
            cur_block = new_block(i)
            if prev_block is not None:
                prev_block.next = cur_block.name
                
        cmd = code[i] % len(machinedef.commands)
        line = decompile_instruction(cmd, code[i+1])
        if not line: continue
        if show_address:  line = line + f" #@{i//2}"
        if cmd == label:
            #End current block
            prev_block = cur_block
            #Start a new one
            cur_block = new_block(i)
            prev_block.next = cur_block.name
        elif cmd in uncond_jumps:
            #end current block
            cur_block.next = blockname(jumpmap[i])
            prev_block = None
            cur_block = None
        elif cmd in true_jumps or cmd in false_jumps:
            iftrue = cmd in true_jumps
            #conditional jump. 
            #current block ends, then conditional op is addde
            prev_block = cur_block
            cond_block = new_condition(i, iftrue, jumpmap[i])
            prev_block.next = cond_block.name
            prev_block = cond_block
            cur_block = None
        else:
            cur_block.lines.append(line)
            cur_block.instructions.append((cmd, code[i+1]))
    if optimize:
        blocks = _detect_dead_branches(blocks, start.name)
        blocks = _eliminate_empty_blocks(blocks)
        _merge_block_chains(blocks)
    return blocks.values()

def _detect_dead_branches(blocks, name_first):

    #no value = block can have any
    block_flag_value = {} #block to tag
    #let's build graph.
    #its nodes are pairs (block, flag value)
    # there are 2 nodes for each actual block.
    # its edges are transitions
    
    graph = defaultdict(list) #map node to next nodes.
    def add_edge(block, flag, next_block, next_flag):
        graph[(block, flag)].append((next_block, next_flag))
        
    #now build this graph
    for block in blocks.values():
        if isinstance(block, Block):
            #plain codeblock
            next_block = blocks[block.next]
            add_edge(block,True, next_block, True)
            add_edge(block,False, next_block, False)
            #does it have flag-changing instructions?
            if _can_change_flag(block):
                add_edge(block,True, next_block, False)
                add_edge(block,False, next_block, True)
        elif isinstance(block, StartBlock):
            #machine starts from False flag
            next_block = blocks[block.next]
            add_edge(block,False,next_block, False)
        elif isinstance(block, CondOp):
            #(block, true) -> jump; (block, false)->next
            if block.iftrue:
                next_true, next_false = block.jump, block.next
            else:
                next_true, next_false = block.next, block.jump
            add_edge(block,True, blocks[next_true], True)
            add_edge(block,False, blocks[next_false], False)
        else:
            raise TypeError(block)
    #Graph is built!!!
    #now find vertices, reachable from the state (block_start, False)
    reachable = set()
    def walk( graphnode ):
        if graphnode in reachable: return
        reachable.add(graphnode)
        for child in graph.get(graphnode,()):
            walk(child)
    walk((blocks[name_first], False))
    del graph
    #good. Now merge the values for reachable blocks
    block2flags = defaultdict(set)
    for block, flag in reachable:
        block2flags[block].add(flag)
    del reachable
    #possible values are () - unreachable block, (True) - reachable by true branches,
    # (False) - reachable by false branches, (True, False)

    trimmed_blocks = {}
    for block in blocks.values():
        flags = block2flags.get(block)
        if not flags:
            #block unreachable!
            continue
        elif isinstance(block, CondOp) and len(flags)==1:
            flag = next(iter(flags))
            #replace block with dummy code block
            if flag == block.iftrue:
                nextblock = block.jump
            else:
                nextblock = block.next
                
            replacement = Block(block.name, [], nextblock)
            trimmed_blocks[replacement.name]=replacement
        else:
            trimmed_blocks[block.name]=block
    return trimmed_blocks

_cmp_instructions = set(c.code for c in machinedef.commands
                        if c.do_changes('b'))
def _can_change_flag(block):
    return any(op in _cmp_instructions
               for op, _ in block.instructions)

def _eliminate_empty_blocks(blocks):
    #simplify block graph by eliminating empty blocks and merging non-empty
    def isempty(block):
        if isinstance(block,Block):
            return not block.lines
        if isinstance(block,CondOp):
            return block.next == block.jump
        return False
    
    def propagate_arrow(targetname):
        target=blocks[targetname]
        if isempty(target):
            return propagate_arrow(target.next)
        else:
            return targetname

    eliminated = {}
    for c in blocks.values():
        if isempty(c): continue
        eliminated[c.name] = c
        c.next = propagate_arrow(c.next)
        if isinstance(c, CondOp):
            c.jump = propagate_arrow(c.jump)
    return eliminated

def _merge_block_chains(blocks):
    block2source = defaultdict(list)
    for c in blocks.values():
        block2source[blocks[c.next]].append(c)
        if isinstance(c,CondOp):
            block2source[blocks[c.jump]].append(c)

    def is_singlesource(c):
        return len(block2source.get(c))==1
    
    merged = {}

    for c in list(blocks.values()):
        if c.name not in blocks: continue
        if not isinstance(c, Block): continue
        
        while True:
            nextc = blocks[c.next]
            if isinstance(nextc, Block) and is_singlesource(nextc):
                #merging it to self.
                c.append(nextc)
                del blocks[c.next]
                c.next = nextc.next
            else:
                break
    

        
            
        
def _dotescape(s):
    return '"' + s.replace('"','\\"').replace("\n","\\n") + '"'
def render_structure_dot(blocks):
    """Render the structure as DOT file"""
    parts = ["digraph Code {"]
    for block in blocks:
        if isinstance(block, Block):
            parts.append("  {name} [shape=box, label={label}]".format(
                name=block.name, label=_dotescape("\n".join(block.lines))))
            parts.append("  {name} -> {next}".format(**block.__dict__))
        elif isinstance(block, StartBlock):
            parts.append("  {name} [shape=oval, label=\"Start\"]".format(
                name=block.name))
            parts.append("  {name} -> {next}".format(**block.__dict__))
        elif isinstance(block, CondOp):
            parts.append("  {name} [shape=diamond, label=\"?\"]".format(
                name=block.name))
            
            if block.iftrue:
                true, false = block.jump, block.next
            else:
                true, false = block.next, block.jump
                
            parts.append("  {block.name} -> {true} [label=\"true\"]".format(**locals()))
            parts.append("  {block.name} -> {false} [label=\"false\"]".format(**locals()))
        else:
            raise TypeError(block)
    parts.append("}")
    return "\n".join(parts)

import os
import subprocess
import shutil
def show_dot(dotcode, png=None, svg=None):
    td = tempfile.mkdtemp()
    tf = os.path.join(td,"diagram.dot")
    try:
        with open(tf,"w") as hf:
            hf.write(dotcode)
        if png:
            subprocess.call(['dot','-Tpng','-o',png, tf])
        elif svg:
            subprocess.call(['dot','-Tsvg','-o',svg, tf])
        else:
            subprocess.call(['dot','-Tx11', tf])
            
            
    finally:
        shutil.rmtree(td)

def show_cleaned_structure(bincode, png=None, optimize=True, wait=True, svg=None):
    def doshow():
        return show_dot(render_structure_dot(parse_structure(bincode, optimize=optimize)),
                        png=png,svg=svg)
    if wait: doshow()
    else:
        from threading import Thread
        t = Thread(target=doshow)
        t.start()
            
def listing(bincode):
    jumpmap = _map_jumps(bincode)
    for i in range(0, len(bincode)-1,2):
        line = decompile_instruction(bincode[i],bincode[i+1])
        if i in jumpmap:
            line = line + "#\t -->{}".format(jumpmap[i])
        print("{}\t{}".format(i,line))
    
    
if __name__=="__main__":
    import nmead
    #bytecode = nmead.nmead_code
    #show_cleaned_structure(bytecode)
    #exit()
    #print(decompile(bytecode))
    #for block in parse_structure(bytecode):
    #    print(block)
    #view in http://viz-js.com/
    #print(render_structure_dot(parse_structure(bytecode)))

    bincode = nmead.nmead_code
    bincode = b'\x83y\x04}\x83\xf2\xf1\xee\xae\xed\xd1=-\xcaD\xfb>\xda\xa2\x9ab7\xdf\xe1\xe0Y}\xd8m\x83\x02\xa2\xb0\xb4\xf8\xbb\x7f`0\x0e\xb1#}\xdd&\xcf\x1c\x97\x1e\x12\xe8[\x06`\x92+4DH\xabi\x02\x9b.\x1ebo\x12\x1d\xeem\xfe\x02 \xfc\xf5c\xf1\x9eF\x81R\xf8E8c\xf4\xf1\xcd\xc2\x91B\x1b\xe68\x02w\xc5\x86\x91\x9e\x0e\x04\xb4t\x8e\x81\xc2`#\xb1\xa58\xcb\xd8\xd8\x04\xb4\x95\x8ev\xc2`\x16\n\x05\x02\x02\x04\x17\n\x01\x03n\x10\x04\x02\x06\x02\x16\n\x02\x02\x11\x1e\x17\n\x01\x00\x08\x10\x04\x01\x02\x01\x01\x00\x04\x02\x02\x02\x11E\x91\x9e\x0e\x04\xb4t\x8e\x02\xc2`#\xb1\xe68\xcb\xd8\xd8\x04\xb4\x95\x8ev\xc2`#\xb1"8\x83y\x04}\x83\xf2\xf1\xcd\xc2qB\xf0\xe68\x02w\xc5\x86\xe6\x02E8c\xf4\xf1\xcd\xc2\x91B\xf0\xe68\x02\xf5c\xf1\x9eF\x81R\xf8E8c\xf4\xf1\xcd\xc2\x91B\xf0\xe68\x02w\xc5\x86\x91\x9e\x0e\x04\xb4t\x8e\x81\xc2`#\xb1\xe68\xcb\xd8\xd8\x04\xb4\x95\x8ev\xc2`#\xb1"8\xdcy\x04}\x83\xf2\xf1\xcd\xc2qB\xf0\xe68\x02w\xc5\x86\x91\x02w\x02\x9b.\x1e#\xb1\xe68\xfb#\xb1r8\xcb\xd8\x04\xb4\x95\x8e\xe8\xc2\xb3\xbbw\xc5\x86\x91\x02w6\x9b.`0\x0e\xb1#}\xdd&\xcf\x1c\xd8\xd8\x04\xb4\x95\x08v\xc2`#\xb1"8\x83y\x04}\x83\xf2>\xcd\xc2qB\xf0\xe68\x02w\xc5\x86\x91\x02w\x02\x9b.\x1e#\xb1\xe68\xfb#\xb1r8\xfe\x02 l\xf5\x95\x8ev\xc2`#\xb1\xe68\x83\x83\xe8\xf8\xf4\xf1\xcd\xc2\x91B\xf0\x9a8\x02w\xc5\x86\x91\x9e\x0e}\xb4t\x8e\x81\xc2`#\xb1\xe68\xfb>\xda\xf5ct\x04\xb4\x95'
    bincode = b'g\x804\xcd}\x804\xcdE \xf5\x8d~4M\x82\xa3\xd7\xc3 \xa3\xcbHH\xdfq\xe8\xb8l\xad&\x89l\xad&\xb8l\x89\x96\\G\xedf\x0c\xd3O\x88v\x0cvPhf0\xc6 f0\xc6 FF\xe6\xaa\x990\xc6 FF\xe6\xaa\x990\xc6 FF\xe6\xaa\x99F\xe6\xaa\x990\xc6 FF\xe6\xaa\x990\xc6 FF\xe6\xaaQ\x91J\xed\xd7nFF\xe6\xaa\x990\xc6 FF\xe6\xaa\x990\xc6 FF\xe6\xaa\x990\xc6 FF\xe6\xaa\x990\xc6 FF\xe6\xaa\x990\xc6 FF\xe6\xaa\x990\xc6 FF\xe6\xaa\x990\xc6 FF\xe6\xaa\x990\xc6 FF\xe6\xaa\x990\xc6 FF\xe6\xaa\x990\xc6 FF\xe6\xaa\x990\xc0 FF\xe6\xaa\x990\xc6 FF\xe6\xaa\x990\xc6 FF\xe6\xaa\x990\xc6 FF\xe6\xaa\x990\xc6 FF\xe6\xaa\x99\xcd$\xd18h\x8a\x82\xa9\xaa\xef\x8bO\xf8\x1f\xa0\x13Q\xc3\x83\xac\x86\xc3\x82\xdfq\x05D\xfb\x8dF\xe6~HR\x82\xdfq\x05D\xfb\x8dF\xe6~H\xdfq\x05\xc6l\x18\x96\\G\xa3\x8d\x80\xa3\xa3\x8d~\xbf>\x8d\xa3\x82\xbf\x80R\x82\xbf\x80\xa3\x80l\x80\xa3\x80l\x8d~\x80\xa3\xb8R,\xbf\x82l\x11\xfe\x82\xbf\x80\x8b\x80l\x8d~\x80\xa3\xb8R,\xbf\x8d\xfe\x82l\x8d~\x80f\xbc\xa3\x82l\x11\xfe\x82l\x8d\xfe\x82l\x8d~\x80f\xbc\xa3\x82l\x11\xfe\x82l\x8d\xfe\x82l\xf2O\x82l\x8dM\\\xdf\xe2\xb8l\xad&l\x8dUv\x0cX^\xc6Uz\x8c\xd7\xf4\x1e}\x05\x02h\xfd\x05\x02h\xfdv\x0cX8bP\xa9Uv\x0cX^\xc6UV\xfdv\x0cX8bP\xa9Uv\x0cV\xfdb\xfd\x0cX8$wx\x83kb\r!\xedf\xeb\xea[\\(fO\x88v\x0ch\xfdv\\8\xa9vI\xa9f\x92\xca\xa9f\x92\xcaO\x88h\xfdv\x0chMl\xb8l\xfdvPhf0\xc6 FF'
    show_cleaned_structure(bincode
                           #, png="nmead-optimized.png"
                           ,svg = "natural.svg"
                           ,optimize=True
    )
