#!/usr/bin/env python
from typing import Any

import argparse
import os
import shutil
import time
import re
import subprocess
from datetime import timedelta
import json
from typing import List
import sys

# The following allows for an absolute import from an adjacent script directory--i.e., up and over instead of down.
# Find the absolute path.
fpath = os.path.dirname(os.getcwd())
fpath = os.path.join(fpath, 'generation_framework/ubkg_utilities')
sys.path.append(fpath)
# Logging module
import ubkg_logging as ulog
# Subprocess handling
import ubkg_subprocess as usub
# config file
import ubkg_config as uconfig


# TODO: make these optional parameters and print them out when --verbose
OWLNETS_SCRIPT: str = './owlnets_script/__main__.py'
FIX_OWLNETS_TSV_SCRIPT: str = './owlnets_script/fix_tsv_file.py'
VALIDATION_SCRIPT: str = './blackbox_validation/__main__.py'
# UMLS_GRAPH_SCRIPT: str = './Jonathan/OWLNETS-UMLS-GRAPH-12.py'
# JAS 16 Mar 2023 renamed folder to OWLNETS-UMLS-GRAPH script.
UMLS_GRAPH_SCRIPT: str = './owlnets_umls_graph/OWLNETS-UMLS-GRAPH-12.py'

# This one needs processing (see https://robot.obolibrary.org/merge ) to include references...
# UBERON_EXT_OWL_URL: str = 'http://purl.obolibrary.org/obo/uberon/ext.owl'

# note: 9/24/21 cl-base, and ccf will not be in the list.
# Jonathan C. Silverstein  11:52 AM 9/24/21
# pato, uberon, cl, doid, ccf-asctb (as ccf), obi, edam, cco, hsapdv, mi, mp, SBO_OWL, chebi
#
# Jonathan C. Silverstein  2:24 PM 9/27/21
# The MI bug is an extraneous paragraph mark in the file - so it doesn’t meet the TSV standard
# MI could come back on the list if a “global replace of paragraph character with space character” in the file fixes it
# - and we can show Tiffany that she is passing those unintentional “white space characters” from OWL files that she
# should be replacing with spaces
# pato, uberon, cl, doid, ccf-asctb (as ccf), obi, edam, cco, hsapdv, mp, SBO_OWL, chebi
#
# Jonathan 2 PM 9/28/21
# remove mp, mi, and cco till we address: OWLNETS files with no labels, and OWLNETS files that are non-conformant TSVs
# Last production build:
# $ ./build_csv.sh -v PATO UBERON CL DOID CCFASCTB OBI EDAM HSAPDV SBO MI CHEBI
# Latest working build (Nov 17, 2021):
# $ ./build_csv.sh -v PATO UBERON CL DOID CCFASCTB OBI EDAM HSAPDV SBO MI CHEBI MP ORDO PR UNIPROTKB
# Approximate run time 26 hrs on a MacBook Pro 2.6 GHz 6-core I7 /w 32 GB 2667 MHz memory
# NOTE: VARIO, and CCO still have problems and so are omitted for now.

# October 13, 2022 - Alan Simmons
# Added ontologies for UO, HUSAT, HUBMAP, and UNIPROTKB so:
# October 15 - PR cross-references UNIPROTKB, so run UNIPROTKB before PR
# $ ./build_csv.sh -v PATO UBERON CL DOID CCFASCTB OBI EDAM HSAPDV SBO MI CHEBI MP ORDO UNIPROTKB PR UO HUSAT HUBMAP

# October 19, 2022 - Alan Simmons
# Added 'organism' argument, primarily for PR.

# November 15, 2022 - Alan simmons
# Drop PR; remove organism argument; add new release of CCF, MONDO
# $ ./build_csv.sh -v PATO UBERON CL DOID OBI EDAM HSAPDV SBO MI CHEBI MP ORDO UNIPROTKB UO HUSAT HUBMAP CCF MONDO

# January 2023 - Alan Simmons
# for SenNet, add parameters EFO, SENNET

# January 2023 - Alan Simmons
# Replaced HUSAT with HRAVS. HRAVS depends on OBIB, XCO, and HRAVS.
# GENERATION ARGUMENTS MOVED TO SEPARATE README: README-PARAMETER ORDER for generation.md


# TODO https://douroucouli.wordpress.com/2019/03/14/biological-knowledge-graph-modeling-design-patterns/


class RawTextArgumentDefaultsHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter
):
    pass


# https://docs.python.org/3/howto/argparse.html
parser = argparse.ArgumentParser(
    description='Build .csv files from source files, including OWL files',
    formatter_class=RawTextArgumentDefaultsHelpFormatter)
parser.add_argument('ontologies', nargs='*')
parser.add_argument("-f", '--ontologies_json', type=str, default='./ontologies.json',
                    help='file containing the ontology definitions referenced by the command line arguments')
parser.add_argument("-u", '--umls_csvs_dir', type=str, default='../neo4j/import/current',
                    help='directory containing the ontology CSV files')
parser.add_argument("-l", "--owlnets_dir", type=str, default='./owlnets_output',
                    help='directory containing the owlnets directories from a run of PheKnowLator')
parser.add_argument("-t", "--owltools_dir", type=str, default='./pkt_kg/libs',
                    help='directory where the PheKnowLator owltools executable is downloaded to')
parser.add_argument("-o", "--owl_dir", type=str, default='./owl',
                    help='directory used for the owl input files')
parser.add_argument("-O", "--oneOwl", type=str, default=None,
                    help='process only this one OWL file')
parser.add_argument("-c", "--clean", action="store_true",
                    help='clean the owlnets_output directory of previous output files before run')
parser.add_argument("-d", "--force_owl_download", action="store_true",
                    help='force downloading of the .owl file before processing')
parser.add_argument("-w", "--with_imports", action="store_true",
                    help='process OWL file even if imports are found, otherwise give up with an error')

# JAS MAY 2023 - Generalized the -s switch
# parser.add_argument("-s", "--skipPheKnowLator", action="store_true",
                    # help='assume that the PheKnowLator has been run and skip the run of it')
parser.add_argument("-s", "--skipBuild", action="store_true",
                    help='skip the building of source files such as OWLNETS and use the existing OWLNETS content')
parser.add_argument("-S", "--skipValidation", action="store_true",
                    help='skip all validation')
parser.add_argument("-v", "--verbose", action="store_true",
                    help='increase output verbosity')
# JAS 15 NOV 2022 - organism argument no longer needed, because PR is no longer ingested.
# JAS 19 October 2022
# parser.add_argument("-p", '--organism', type=str, default='human',
                    # help='organism (e.g., human, mouse)')

args = parser.parse_args()


def make_new_save_dir(path: str, save_dir: str) -> str:
    max_version: int = 0
    for filename in os.listdir(path):
        if re.match(f'^{save_dir}\.[0-9].*$', filename):
            current_version: int = int(filename.split('.', 1)[1])
            max_version = max(max_version, current_version)
    new_dir: str = f"{save_dir}.{max_version+1}"
    new_path: str = os.path.join(path, new_dir)
    os.mkdir(new_path)
    return new_path


def copy_csv_files_to_save_dir(path: str, save_dir: str) -> str:
    save_path: str = make_new_save_dir(path, save_dir)
    ulog.print_and_logger_info(f"Saving .csv files to directory: {save_path}")
    for filename in os.listdir(path):
        if re.match(f'^.*\.csv$', filename):
            fp_src: str = os.path.join(path, filename)
            fp_dst: str = os.path.join(save_path, filename)
            shutil.copyfile(fp_src, fp_dst)
    ulog.print_and_logger_info(f"Copied {len(os.listdir(save_path))} files from {path} to {save_path}")
    return save_path


def lines_in_file(path: str) -> int:
    return int(subprocess.check_output(f"/usr/bin/wc -l {path}", shell=True).split()[0])


def lines_in_csv_files(path: str, save_path: str) -> None:
    for filename in os.listdir(path):
        if re.match(f'^.*\.csv$', filename):
            fp: str = os.path.join(path, filename)
            lines_fp: int = lines_in_file(fp)
            fp_save: str = os.path.join(save_path, filename)
            lines_fp_save: int = lines_in_file(fp_save)
            ulog.print_and_logger_info(f"Lines in files: {fp} {lines_fp}; {fp_save} {lines_fp_save}; difference: "
                                       f"{lines_fp-lines_fp_save}")


def verify_ontologies_json_file(ontologies: dict, ontologies_filename: str) -> None:
    valid_ontology_keys: List[str] = \
        ['owl_url', 'home_url', 'comment', 'sab', 'download_owl_url_to_file_name', 'execute']
    for key, value in ontologies.items():
        if not key.isupper():
            ulog.print_and_logger_info(f"For the Ontologies file {ontologies_filename}: the ontology key "
                                       f"{key} must be upper case.")
            exit(1)
        for key_o in value:
            if key_o not in valid_ontology_keys:
                ulog.print_and_logger_info(f"For the Ontologies file {ontologies_filename} with ontology key "
                                           f"{key}: {key_o} must be one of: {', '.join(valid_ontology_keys)}")
                exit(1)


# Fix files that have tabs in the descriptions and therefore broken records (while saving the original file)...
def fix_owlnets_metadata_file(working_owlnets_dir: str) -> None:
    owlnets_metadata_file: str = os.path.join(working_owlnets_dir, 'OWLNETS_node_metadata.txt')
    owlnets_metadata_orig_file: str = os.path.join(working_owlnets_dir, 'OWLNETS_node_metadata_orig.txt')
    # JAS 4 APR 2023 - Replaced os.system call with subprocess and error handling.
    # os.system(f"mv {owlnets_metadata_file} {owlnets_metadata_orig_file}")
    usub.call_subprocess(f"mv {owlnets_metadata_file} {owlnets_metadata_orig_file}")

    fix_owlnets_tsv_script: str = f"{FIX_OWLNETS_TSV_SCRIPT} --fix {owlnets_metadata_file} {owlnets_metadata_orig_file}"
    ulog.print_and_logger_info(f"Running: {fix_owlnets_tsv_script}")
    # os.system(fix_owlnets_tsv_script)
    usub.call_subprocess(fix_owlnets_tsv_script)


def get_ubkg_context(sablist: List[str]) -> List[str]:
    # JAS MAY 2023
    # A UBKG context corresponds to a set of SABs that are ingested in a particular order.
    # UBKG contexts can be defined in an optional configuration file.

    # Returns a list of SABs in a particular context.
    # sablist - list of SABs passed to the script.

    context = ''

    # Read from config file, if one exists.
    cfgfile = os.path.join(os.path.dirname(os.getcwd()), 'generation_framework/contexts.ini')
    if os.path.isfile(cfgfile):
        cfg = uconfig.ubkgConfigParser(cfgfile)
        contextkey = sablist[0]
        base = cfg.get_value(section='Base Context', key='base')
        if contextkey == 'base':
            context = base
        if contextkey in cfg.config['Contexts']:
            context = base + ' ' + cfg.get_value(section='Contexts', key=contextkey)

    return context.upper().split(' ')

# ----------------------------
# Start of main script

# ontology_names = [s.upper() for s in args.ontologies]
# JAS MAY 2023 - UBKG contexts
# Check whether the argument corresponds to one of the UBKG contexts--e.g., base, hmsn, dd


ubkg_context = get_ubkg_context(args.ontologies)
if ubkg_context[0] == '':
    # The argument list is a collection of SABs, not necessarily equivalent to the set in a UBKG context.
    ontology_names = [s.upper() for s in args.ontologies]
else:
    ontology_names = ubkg_context

if args.verbose is True:
    print('Parameters:')
    print(f" * Verbose mode")
    if args.clean is True:
        print(" * Cleaning owlnets directory")
    print(f" * ontologies.json file: {args.ontologies_json} (exists: {os.path.isfile(args.ontologies_json)})")
    print(f" * Owlnets directory: {args.owlnets_dir} (exists: {os.path.isdir(args.owlnets_dir)})")
    print(f" * Owltools directory: {args.owltools_dir} (exists: {os.path.isdir(args.owltools_dir)})")
    print(f" * Owl directory: {args.owl_dir} (exists: {os.path.isdir(args.owl_dir)})")
    if len(ontology_names) > 0:
        print(f" * Ontologies to process: {', '.join(ontology_names)}")
    umls_csvs_dir_islink = False
    if os.path.islink(args.umls_csvs_dir) is True:
        umls_csvs_dir_islink = os.path.realpath(args.umls_csvs_dir)
    print(f" * Directory containing the UMLS Graph Extract .csv files to process: {args.umls_csvs_dir} "
          f"(exists: {os.path.isdir(args.umls_csvs_dir)}) (simlink: {umls_csvs_dir_islink})")
    if args.force_owl_download is True:
        print(f" * PheKnowLator will force .owl file downloads")
    if args.with_imports is True:
        print(f" * PheKnowLator will run even if imports are found in .owl file")
    if args.skipBuild is True:
        print(f" * Skip the build of content in OWLNETS path")
    # if args.skipPheKnowLator is True:
         # print(f" * Skip PheKnowLator run")
    if args.oneOwl is not None:
        print(f" * Process only one OWL file: {args.oneOwl}")
    if args.skipValidation is True:
        print(' * Skipping all validation')
    # JAS 15 NOV 2022 - The organism argument is no longer needed.
    # JAS 19 OCT 2022
    # print(f' * Organism: {args.organism}')
    print('')

ontologies = json.load(open(args.ontologies_json, 'r'))
verify_ontologies_json_file(ontologies, args.ontologies_json)

missing_ontology = False
if len(ontology_names) > 0 or args.oneOwl is not None:
    if args.oneOwl is not None:
        ontology_names = [args.oneOwl]
    for ontology_name in ontology_names:
        if ontology_name not in ontologies:
            ulog.print_and_logger_info(f"ERROR... Ontology name ''{ontology_name}'' not found in ontologies.json")
            missing_ontology = True
else:
    ulog.print_and_logger_info("ERROR: No ''ontologies'' specified on the command line? Use -h for help.")
    exit(1)
if missing_ontology is True:
    ulog.print_and_logger_info(f"Exiting since some ontologies specified were not found in the ontology.json file.")
    exit(1)

start_time = time.time()

ulog.print_and_logger_info(f"Processing Ontologies: {', '.join(ontology_names)}")

for ontology_name in ontology_names:
    ulog.print_and_logger_info('*********************************************')
    ulog.print_and_logger_info(f"Ontology: {ontology_name}")
    ontology_record = ontologies[ontology_name]

    owl_sab: str = ontology_name.upper()
    if 'sab' in ontology_record:
        owl_sab: str = ontology_record['sab'].upper()
    working_owlnets_dir: str = os.path.join(args.owlnets_dir, owl_sab)

    if 'execute' not in ontology_record and args.skipBuild is not True:
        owl_url = ontology_record['owl_url']
        ulog.print_and_logger_info(f"Processing OWL file: {owl_url}")
        clean = ''
        if args.clean is True:
            clean = '--clean'
        force_owl_download = ''
        if args.force_owl_download is True:
            force_owl_download = '--force_owl_download'
        with_imports = ''
        if args.with_imports is True:
            with_imports = '--with_imports'
        if args.verbose is True:
            verbose = '--verbose'
        owlnets_script: str = f"{OWLNETS_SCRIPT} --ignore_owl_md5 {clean} {verbose} {force_owl_download} " \
                              f"{with_imports} -l {args.owlnets_dir} -t {args.owltools_dir} " \
                              f"-o {args.owl_dir} {owl_url} {owl_sab}"
        ulog.print_and_logger_info(f"Running: {owlnets_script}")
        # JAS APR 2023 replaced call to os.system
        # os.system(owlnets_script)
        usub.call_subprocess(owlnets_script)

        fix_owlnets_metadata_file(working_owlnets_dir)
    # JAS MAY 2023 Generalized skip of build to include paths other than PheKnowLator
    elif 'execute' in ontology_record and args.skipBuild is not True:
        script: str = ontology_record['execute']
        ulog.print_and_logger_info(f"Running: {script}")
        # JAS 4 APR 2023 replaced call to os.system
        # os.system(script)
        usub.call_subprocess(script)
    # JAS 13 OCT 2022 - allows skipping of PheKnowLator processing
    elif 'execute' in ontology_record:
        ulog.print_and_logger_info(f"Skipping build processing for Ontology: {ontology_name}.")
        ulog.print_and_logger_info("Assuming that current OWLNETS files are available.")
        script: str = ontology_record['execute'] + ' -s'
        ulog.print_and_logger_info(f"Running: {script}")
        usub.call_subprocess(script)
    # else:
        # ulog.print_and_logger_info(f"ERROR: There is no processing available for Ontology: {ontology_name}?!")

    # if args.skipValidation is not True:
    #     validation_script: str = f"{VALIDATION_SCRIPT} -o {args.umls_csvs_dir} -l {bargs.owlnets_dir}"
    #     logger.info(f"Running: {validation_script}")
    #     os.system(validation_script)

    # JAS JANUARY 2024 - Deprecate copy of CSVs to save directories.
    # save_csv_dir = copy_csv_files_to_save_dir(args.umls_csvs_dir, 'save')

    # JAS 15 nov 2022 - removed organism argument
    # JAS 19 OCT 2022 added organism argument

    # JAS July 2023 - Do not call UMLS_GRAPH_SCRIPT for the initial UMLS reformatting.
    if owl_sab != 'UMLS':
        umls_graph_script: str = f"{UMLS_GRAPH_SCRIPT} {working_owlnets_dir} {args.umls_csvs_dir} {owl_sab}"
        ulog.print_and_logger_info(f"Running: {umls_graph_script}")

        # JAS 4 APR 2023 - Replaced os.system call with subprocess and error handling.
        # os.system(umls_graph_script)
        usub.call_subprocess(umls_graph_script)

        # JAS JANUARY 2024 - Deprecate saving copies of CSVs to save directory.
        # lines_in_csv_files(args.umls_csvs_dir, save_csv_dir)

    # Add log entry for how long it took to do the processing...
    elapsed_time = time.time() - start_time
    ulog.print_and_logger_info(f'Done! Total Elapsed time {"{:0>8}".format(str(timedelta(seconds=elapsed_time)))}')
