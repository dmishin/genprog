import numpy as np
import json
import argparse
import machinedef

class SkipLine(Exception):pass

def parseline(line):
    if line[0] != "{": return parseline_legacy(line)
    data = json.loads(line)
    if 'hexcode' not in data: raise SkipLine()
    (dist, neval, steps, size) = data['fitness']
    code = bytes.fromhex(data['hexcode'])
    return -dist, -neval, code, data.get('command_system_hash')

def parseline_legacy(line):
    sgen, srest = line.split('\t',1)
    gen = int(sgen)
    ((dist, neval, steps, size),code) = eval(srest)
    return -dist, -neval, code, None
    
def parselog(logfile):
    dists = []
    evals = []
    codes = []
    with open(logfile,'r') as h:
        for line in h:
            try:
                dist,neval,code,cshash = parseline(line)
                dists.append(dist)
                evals.append(neval)
                codes.append((code,cshash))
            except SkipLine:
                pass
            except Exception as err:
                print("Error reading line:", err)
    return dists, evals, codes

if __name__=="__main__":
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument("logfile",
                        help="Log file for parsing")
    args = parser.parse_args()
    
    dists, evals, codes = parselog(args.logfile)
    print(f"Loaded {len(codes)} log points")
    if not codes:
        print("Nothing to show")
        exit(0)
        
    from matplotlib import pyplot as pp

    fig, (ax1, ax2) = pp.subplots(nrows=2, ncols=1, sharex=True)

    def onclick(event):
        print('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
              ('double' if event.dblclick else 'single', event.button,
               event.x, event.y, event.xdata, event.ydata))
        if event.button == 3:
            from analyser import show_cleaned_structure
            x = int(round(event.xdata))
            if x < 0: x = 0
            code, cshash = codes[x]
            print(f"{args.logfile}:{x}")
            if cshash is None:
                print("Warning: no code system specified")
            else:
                if cshash!=machinedef.command_system_hash():
                    print(f"Warning! command system does not match, expected {machinedef.command_system_hash()}, got {cshash}")
            show_cleaned_structure(code,wait=False)
    cid = fig.canvas.mpl_connect('button_press_event', onclick)
    
    ax1.semilogy(dists)
    ax2.semilogy(evals)
    pp.show()
