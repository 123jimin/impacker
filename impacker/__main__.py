import argparse
from pathlib import Path

from . import SourceCode, Impacker

parser = argparse.ArgumentParser(prog="impacker", description="Merge a Python code and its dependencies into a single file.")

parser.add_argument('-c', '--compress-lib', help="compress packed library codes", action='store_true')
parser.add_argument('-v', '--verbose', help="prints verbose log", action='store_true')
parser.add_argument('--no-shake-tree', dest='shake_tree', help="do not shake import tree", action='store_const', const=False, default=True)

parser.add_argument('in_file', metavar='IN_FILE', type=Path, help="code file to pack")
parser.add_argument('out_file', metavar='OUT_FILE', type=Path, help="name of file to generate")

args = parser.parse_args()

in_file = args.in_file
out_file = args.out_file

delattr(args, 'in_file')
delattr(args, 'out_file')

impacker = Impacker(**vars(args))
in_code = SourceCode.from_path(in_file)

out_code = impacker.pack(in_code)
with open(out_file, 'w') as f:
    f.write(out_code)