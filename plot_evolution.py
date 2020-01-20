import numpy as np
def parselog(logfile):
    dists = []
    evals = []
    codes = []
    with open(logfile,'r') as h:
        for line in h:
            try:
                sgen, srest = line.split('\t',1)
                gen = int(sgen)
                ((dist, neval, steps, size),code) = eval(srest)
                dists.append(-dist)
                evals.append(-neval)
                codes.append(code)
            except Exception as err:
                print("Error reading line:", err)
    return dists, evals, codes

if __name__=="__main__":
    import sys
    dists, evals, codes = parselog(sys.argv[1])

    from matplotlib import pyplot as pp

    fig, (ax1, ax2) = pp.subplots(nrows=2, ncols=1, sharex=True)

    def onclick(event):
        print('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
              ('double' if event.dblclick else 'single', event.button,
               event.x, event.y, event.xdata, event.ydata))
        if event.button == 3:
            from disassembler import show_cleaned_structure
            code = codes[event.x]
            print(code)
            show_cleaned_structure(code,wait=False)
    cid = fig.canvas.mpl_connect('button_press_event', onclick)
    
    ax1.semilogy(dists)
    ax2.plot(evals)
    pp.show()
