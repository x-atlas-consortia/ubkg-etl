"""
Script that checks each row of a CSV file to verify that it has the same number of columns as the header.
If --fix=True, pads or truncates the columns in the output file to match the number of header columns.
"""
import csv
import sys
import os

def check_and_fix_csv(input_file, output_file=None, fix=False):
    with open(input_file, newline='', encoding='utf-8') as f:
        reader = list(csv.reader(f))
    header = reader[0]
    header_len = len(header)
    problem_lines = []

    fixed_rows = [header]
    for idx, row in enumerate(reader[1:], start=2):  # Line numbers start at 2 for data rows
        if len(row) != header_len:
            #print(f'length of row: {len(row)} vs {header_len}')
            problem_lines.append((idx, len(row), row))
            if fix:
                # Truncate or pad the row to match the header
                if len(row) > header_len:
                    row = row[:header_len]
                else:
                    row += [''] * (header_len - len(row))
        fixed_rows.append(row)

    # Report
    if problem_lines:
        print(f"Found {len(problem_lines)} problem lines:")
        for line_no, row_len, row in problem_lines:
            print(f"Line {line_no}: {row_len} columns -- {row}")
    else:
        print("No problems found!")

    # Optionally write fixed file
    if fix and output_file:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(fixed_rows)
        print(f"Fixed file written to {output_file}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Check and optionally fix CSV column counts.")
    parser.add_argument("-u", '--umls_csvs_dir', type=str, default='../../neo4j/import/current',
                        help='directory containing the ontology CSV files')
    parser.add_argument("input_csv", help="Input CSV file")
    parser.add_argument("--fix", action="store_true", help="Auto-fix rows with wrong number of columns")
    parser.add_argument("--output", default="fixed.csv", help="Output CSV file if fixing")
    args = parser.parse_args()
    check_and_fix_csv(input_file=os.path.join(args.umls_csvs_dir,args.input_csv), output_file=os.path.join(args.umls_csvs_dir,args.output) if args.fix else None, fix=args.fix)