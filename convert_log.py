#convert log from legacy format to JSON
import sys, json
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("logfile",
                    nargs="+",
                    help="Log file for parsing")
args = parser.parse_args()

for logfile in args.logfile:
    print("Converting", logfile)
    with open(logfile, "r") as hfile:
        with open(logfile+".jsons", "w") as ofile:
            for line in hfile:
                try:
                    sgen, srest = line.split('\t',1)
                    gen = int(sgen)
                    (fitness,code) = eval(srest)
                except Exception as err:
                    print("Failed to parse line:",err)
                    continue
                ofile.write(json.dumps({
                    'generation':gen,
                    'fitness': fitness,
                    'hexcode': code.hex()
                }))
                ofile.write("\n")
            
    print("  Converted OK")
