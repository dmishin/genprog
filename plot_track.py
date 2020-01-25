from machine import randomize, Machine, FunctionTable, command_system_hash
from matplotlib import pyplot
import numpy as np
import argparse
from utils import load_code

def get_tracks(code, funcindex, steps):
    m = Machine()
    m.set_function(FunctionTable(funcindex))
    m.load_code(code)

    ncalls = []
    registers_with_time=[[] for _ in range(16)]
    fregisters_with_time=[[] for _ in range(16)]
    
    def check_changes(t):
        ncalls.append(m.ncalls)
        for idx, track in enumerate(registers_with_time):
            value = m.get_vec_reg(idx)
            track.append(value)
            
        for idx, track in enumerate(fregisters_with_time):
            value = m.get_float_reg(idx)
            track.append(value)

    for t in range(steps):
        check_changes(t)
        m.step()
    return ncalls, registers_with_time, fregisters_with_time

def plot_tracks(calls, vecs, floats, x0, y0, style=""):
    #pyplot.subplot('121')
    for idx, track in enumerate(vecs):
        xs = [x for (x,_) in track]
        ys = [y for (_,y) in track]
        
        _,r = logtfm(x0,y0,xs,ys)
        pyplot.plot(calls,r,style)
        pyplot.xlabel("$N_{eval}$")
        pyplot.ylabel("$\\log(v-x_0)$")
    #pyplot.subplot('122')
    #for idx, track in enumerate(floats):
    #    pyplot.plot(calls,track,style)
    #    pyplot.xlabel("$N_{eval}$")
    #    pyplot.ylabel("Register value")

        
log10 = np.log(10)
def logtfm(x0,y0,x,y):
    x=np.array(x)-x0
    y=np.array(y)-y0
    return (np.arctan2(x,y)), np.log(x**2+y**2)*0.5/log10

def doplot(code, nfunc, x0, y0, steps):
    calls, vecs, floats = get_tracks(code, nfunc, steps)
    plot_tracks(calls, vecs, floats,
                x0, y0,
                style=""
    )
    
if __name__=="__main__":
    randomize()
    parser = argparse.ArgumentParser()
    parser.add_argument("codefile",
                        nargs='+',
                        help="Input code files, in JSON format")
    args = parser.parse_args()
    
    for fname in args.codefile:
        code = load_code(fname,command_system_hash())
        
        calls, vecs, floats  = get_tracks(code, 0, 5000)
        plot_tracks(calls, vecs[0:1], floats,
                    1.0, 1.0,
                    style="k-"
        )
    pyplot.legend()
    pyplot.show()

