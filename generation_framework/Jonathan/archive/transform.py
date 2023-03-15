#!/usr/bin/env python

import argparse
import os
import re


class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass


# https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(
    description='Transform the input python file generated from a notebook',
    formatter_class=RawTextArgumentDefaultsHelpFormatter)
parser.add_argument('filename', type=str,
                    help='input python file')
args = parser.parse_args()

print(f"Processing input file {args.filename}")
lines = []
with open(args.filename, "r") as file:
    lines = file.readlines()
    lines = [line.rstrip() for line in lines]

    if lines[0] != '#!/usr/bin/env python':
        print('ERROR: Was expectin a python file?!')
        exit(1)

    # Add wrapper functions to include the directory as args to the python file
    pos = lines.index('import os')
    lines[pos+1:pos+1] = [
        '',
        '',
        'def owlnets_path(file: str) -> str:',
        '    return os.path.join(sys.argv[1], file)',
        '',
        '',
        'def csv_path(file: str) -> str:',
        '    return os.path.join(sys.argv[2], file)',
        ''
    ]

    # Add the wrapper to the input lines...
    for idx, line in enumerate(lines):
        r_m = re.match(r'(.*pd.read_csv\()(\".*\.txt\")(, sep=\'\\t\'.*)', line)
        if r_m:
            lines[idx] = r_m[1] + 'owlnets_path(' + r_m[2] + ')' + r_m[3]
            continue
        w_m = re.match(r'(.*\.to_csv\()(\'.*\.csv\')(.*)', line)
        if w_m:
            lines[idx] = w_m[1] + 'csv_path(' + w_m[2] + ')' + w_m[3]
            continue
        w_m = re.match(r'(.*\.read_csv\()(\".*\.csv\")(.*)', line)
        if w_m:
            lines[idx] = w_m[1] + 'csv_path(' + w_m[2] + ')' + w_m[3]
            continue
        sab = re.match(r'(^OWL_SAB = )\'.*\'', line)
        if sab:
            lines[idx] = sab[1] + 'sys.argv[3].upper()'
            continue

with open(args.filename, "w") as file:
    file.writelines(line + '\n' for line in lines)

os.system(f'chmod +x {args.filename}')
