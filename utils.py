import json
import sys
import re
import os

def load_code(jsonfile, check_hash=None):
    m=re.match(r"^(.+?):(-?\d+)", jsonfile)
    if m:
        basefile, sline = m.groups()
        return load_line(basefile, int(sline), check_hash)
    
    with open(jsonfile) as hfile:
        return _get_code(jsonfile, json.load(hfile), check_hash)
        
def _get_code(jsonfile, data, check_hash):
    if check_hash:
        if 'command_system_hash' in data:
            if check_hash != data['command_system_hash']:
                print(f"Warning! file {jsonfile} specifies code system {data['command_system_hash']}, while expected is {check_hash}", file=sys.stderr)
        else:
            print(f"Warning! file {jsonfile} specifies no code system", file=sys.stderr)
    if 'hexcode' in data:
        return bytes.fromhex(data['hexcode'])
    elif 'bincode' in data:
        return data['bincode']
    raise ValueError(f"File {jsonfile} has no 'hexcode' or 'bincode' field")
    

def load_line(jsonfile, nline, check_hash=None):
    try:
        idx = load_index(jsonfile)
        offset=idx['offsets'][nline]            
        with open(jsonfile,"r") as hfile:
            hfile.seek(offset)
            line = hfile.readline()
        return _get_code(jsonfile+":"+str(nline), json.loads(line), check_hash)
    except IndexError:
        raise ValueError(f"Line {nline} not found in {jsonfile}")


def load_index(jsonsfile):
    indexfile = jsonsfile+".index"
    if os.path.exists(indexfile):
        if os.path.getmtime(indexfile) < os.path.getmtime(jsonsfile):
            print("Updating index")
            idx = _create_index(jsonsfile, indexfile)
        else:
            with open(indexfile,"r")as h:
                idx = json.load(h)
    else:
        print("Creating index")
        idx = _create_index(jsonsfile, indexfile)
    return idx

def _create_index(jsonsfile, indexfile):
    offsets = []
    
    with open(jsonsfile, "r") as hfile:
        while True:
            pos = hfile.tell()
            line = hfile.readline()
            if not line: break
            offsets.append(pos)
    idx = {'offsets':offsets}
    with open(indexfile,"w") as hidx:
        json.dump(idx, hidx)
    print(f"Created index file {indexfile} with {len(offsets)} entries")
    return idx
