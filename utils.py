import json
import sys

def load_code(jsonfile, check_hash=None):
    with open(jsonfile) as hfile:
        data = json.load(hfile)
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
