import assembler
import os

with open(os.path.join(os.path.dirname(__file__),"nmead.txt"), "r") as hfile:
    nmead_code = assembler.compile_code(hfile.read())

