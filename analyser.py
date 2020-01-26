import re
from collections import defaultdict
import tempfile
import os
import subprocess
import shutil
import machinedef
from disassembler import decompile_instruction, map_jumps

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
    jumpmap = map_jumps(code)

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
        visited = set((target,))
        while isempty(target):
            targetname = target.next
            target = blocks[targetname]
            if target in visited:
                #loop of empty blocks...
                break
            else:
                visited.add(target)
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
            
if __name__=="__main__":
    import nmead
    from utils import load_code
    import argparse
    import os
    
    parser = argparse.ArgumentParser()
    parser.add_argument("codefile",
                        help="Input code file, in JSON format")
    parser.add_argument("-o", "--output", help="Save generated diagram as (default is show)")
    parser.add_argument("-t", "--format", help="Output format. Can be SVG or PNG")
    
    args = parser.parse_args()

    bincode = load_code(args.codefile, check_hash=machinedef.command_system_hash())

    png, svg = None, None
    if args.output:
        if output.format:
            fmt = output.format.lower()
        else:
            fmt = os.path.splitext(args.output)[1][1:].lower()
        if fmt=="svg":
            svg = args.output
        elif fmt == "png":
            png = args.output
        else:
            raise ValueError(f"Bad format: {fmt}, can be svg or png")
    
    show_cleaned_structure(bincode
                           ,png= png
                           ,svg=svg
                           ,optimize=True
    )
