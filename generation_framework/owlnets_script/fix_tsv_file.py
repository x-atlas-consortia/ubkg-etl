#!/usr/bin/env python

import argparse, os, re, unicodedata, sys, string


class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass


# https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(
    description='Post process tsv files produced py PheKnowLator',
    formatter_class=RawTextArgumentDefaultsHelpFormatter)
parser.add_argument('filename', type=str,
                    help='file or directory to fix')
parser.add_argument("-c", "--check", action="store_true",
                    help='check that all records have the same number of fields; exit status 0 when no bad records,'
                         ' else 1')
parser.add_argument("-f", "--fix", type=str,
                    help='for records with fewer fields, append lines till the field count is correct;'
                         ' then do an implicit --check on the output file')
parser.add_argument("-a", "--all", action="store_true",
                    help='fix all OWLNETS_node_metadata.txt files in the filename which should be a directory')
parser.add_argument("-v", "--verbose", action="store_true",
                    help='increase output verbosity')
args = parser.parse_args()


def print_string_as_chars(s: str) -> None:
    print(s)
    lst = [ord(c) for c in s]
    print(lst)


def count_of_char_in_str(ch: int, s: str) -> int:
    lst = [ord(c) for c in s]
    return lst.count(ch)


def check(ifilename: str) -> int:
    print(f"Checking file {ifilename}...")
    file_r = open(ifilename, 'r')

    # Process the header to determine the number of fields in a record...
    line = file_r.readline()
    tabs_in_record = line.count('\t')
    print(f"Fields in record: {tabs_in_record}")

    line_no = 1
    bad_no = 0
    eof = False
    while not eof:
        line_no += 1
        line = file_r.readline()
        # print_string_as_chars(line)

        # if line is empty end of file is reached
        if not line:
            break
        tabs_in_line = line.count('\t')
        # print(f"tabs_in_line: {tabs_in_line}; tabs_in_record: {tabs_in_record}")

        line_no_initial = line_no
        while not eof and tabs_in_line < tabs_in_record:
            if args.verbose is True:
                print(f"< Line number {line_no_initial}:{line_no} has {tabs_in_line} fields but wanted {tabs_in_record}, last character {ord(line[-1])}")
            bad_no += 1
            line_no += 1
            next_line = file_r.readline()
            if not next_line:
                eof = True
                break
            line = line + ' ' + next_line
            tabs_in_line = line.count('\t')
        if tabs_in_line > tabs_in_record:
            if args.verbose is True:
                print(f"> Line number {line_no} has {tabs_in_line} fields but wanted {tabs_in_record}, last character {ord(line[-1])}")
            bad_no += 1

    print(f"Lines in file: {line_no}, bad records: {bad_no}")
    file_r.close()
    if bad_no == 0:
        return 0
    return 1


def fix_records_to_have_same_number_of_fields(ifilename: str, ofilename: str) -> None:
    print(f"Fixing file {ifilename}, saving to file {ofilename}...")
    file_w = open(ofilename, 'w')
    file_r = open(ifilename, 'r')

    # Process the header to determine the number of fields in a record...
    line = file_r.readline()
    tabs_in_record = line.count('\t')
    print(f"Fields in record: {tabs_in_record}")
    file_w.write(line)

    appended = 0
    line_no = 1
    eof = False
    while not eof:
        line_no += 1
        line = file_r.readline()

        # if line is empty end of file is reached
        if not line:
            break
        tabs_in_line = line.count('\t')

        line_no_initial = line_no
        while not eof and tabs_in_line < tabs_in_record:
            if args.verbose is True:
                print(f"< Line number {line_no_initial}:{line_no} has {tabs_in_line} fields but wanted {tabs_in_record}, last character {ord(line[-1])}")
            # This should be a new line character, so remove it
            line = line[:-1]
            line_no += 1
            next_line = file_r.readline()
            if not next_line:
                eof = True
                break
            appended += 1
            line = line + ' ' + next_line
            tabs_in_line = line.count('\t')
        if tabs_in_line > tabs_in_record:
            if args.verbose is True:
                print(f"> Line number {line_no} has {tabs_in_line} fields but wanted {tabs_in_record}, last character {ord(line[-1])}")

        file_w.write(line)

    print(f"Lines in file: {line_no}, lines appended: {appended}")
    file_w.close()
    file_r.close()


def all(dir: str) -> int:
    if not os.path.isdir(dir):
        print(f"Filename when using --all must be a directory")
        exit(1)
    print(f"Checkinging all OWLNETS_node_metadata.txt files in the directory {dir}")
    check_errors = 0
    for dir2 in os.listdir(dir):
        dir2_path = os.path.join(dir, dir2)
        if os.path.isdir(dir2_path):
            file_path = os.path.join(dir2_path, 'OWLNETS_node_metadata.txt')
            if not os.path.isfile(file_path):
                print(f"ERROR: {file_path} not found or not a file?")
                continue
            if check(file_path) == 0:
                print(f"File {file_path} is well formed, skipping fix...")
                continue
            print(f"File {file_path} contains errors fixing...")
            file_orig_path = os.path.join(dir2_path, 'OWLNETS_node_metadata_orig.txt')
            os.rename(file_path, file_orig_path)
            fix_records_to_have_same_number_of_fields(file_orig_path, file_path)
            check_exit_status = check(file_path)
            if check_exit_status != 0:
                print(f"ERROR: {file_path} check after fix revealed errors?!")
                check_errors += 1
    if check_errors == 0:
        return 0
    return 1


print(f"Processing {args.filename}")

if not os.path.exists(args.filename):
    print(f"ERROR: The file or directory to fix '{args.filename}' does not exist?!")
    exit(1)

exit_status: int = 0
if args.fix is not None:
    fix_records_to_have_same_number_of_fields(args.filename, args.fix)
if args.check is True or args.fix is True:
    exit_status = check(args.filename)
if args.all is True:
    exit_status = all(args.filename)

print('Done!')
exit(exit_status)
