import argparse
import bibtexparser
import time
import re
import os
import glob

def clean(input_string):
    # Use regular expression to remove non-alphabetic characters
    output_string = re.sub(r'[^a-zA-Z]', '', input_string)
    return output_string

def read_bib_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as bibfile:
        return bibtexparser.load(bibfile)


def remove_entries_without_field(bib_database, field):
    removed_entries = []
    new_entries = []
    for entry in bib_database.entries:
        if field not in entry:
            removed_entries.append(entry)
        else:
            new_entries.append(entry)
    bib_database.entries = new_entries
    return bib_database, removed_entries

def merge_bib_databases(*bib_databases, field):
    merged_bib_database = bibtexparser.bibdatabase.BibDatabase()
    merged_set = set()
    for bib_database in bib_databases:
        for entry in bib_database.entries:
            if field in entry and clean(entry[field].lower()) not in merged_set:
                merged_bib_database.entries.append(entry)
                merged_set.add(clean(entry[field].lower()))
    return merged_bib_database


def find_intersection(bib_database1, bib_database2, field):
    intersection = []
    entries_set = {entry[field].lower() for entry in bib_database1.entries}
    for entry in bib_database2.entries:
        if entry[field].lower() in entries_set:
            intersection.append(entry)
    return intersection

def find_difference(bib_database1, bib_database2, field):
    difference = []
    entries_set = {entry[field].lower() for entry in bib_database2.entries}
    for entry in bib_database1.entries:
        if entry[field].lower() not in entries_set:
            difference.append(entry)
    return difference

def write_bib_file(file_path, bib_database):
    with open(file_path, 'w', encoding='utf-8') as bibfile:
        bibtexparser.dump(bib_database, bibfile)

def filter_entries_by_regex(bib_database, fields, regex_include=None, regex_exclude=None):
    filtered_entries = []
    for entry in bib_database.entries:
        if regex_exclude and any(re.search(regex_exclude, entry.get(field, ""), re.IGNORECASE) for field in fields if field in entry):
            continue  # Skip this entry if the regex_exclude matches any of the fields
        if regex_include is None or any(re.search(regex_include, entry.get(field, ""), re.IGNORECASE) for field in fields if field in entry):
            filtered_entries.append(entry)
    return filtered_entries

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Perform operations on .bib files.')
    parser.add_argument('-f',required=True,nargs='+',default='doi', help='Field for comparison (default is "doi")')
    parser.add_argument('-list',required=False, help='Print the entries in a list (one per line)')
    parser.add_argument('-include', default='', help='Regex expression for inclusion')
    parser.add_argument('-exclude', default='', help='Regex expression for exclusion')
    parser.add_argument('-op',required=False, choices=['m', 'd', 'i'], help='Choose m for merge, d for difference or i for intersection')
    parser.add_argument('-in',required=False, nargs='+',dest="infiles", help='List of .bib input files')
    parser.add_argument('-dir', required=False, dest='dir_path', help='Directory path to read all .bib files (mutually exclusive with -in)')
    parser.add_argument('-out',required=True,dest='output_file', help='Output .bib file name or threshold percentage')
    args = parser.parse_args()

    if not args.infiles and not args.dir_path:
        parser.error("Please provide either -in with a list of .bib files or -dir with a directory path containing .bib files.")
    elif args.infiles and args.dir_path:
        parser.error("-in and -dir options are mutually exclusive. Please choose one.")


    bib_files=None
    start = time.time()
    if args.dir_path:
        if not os.path.isdir(args.dir_path):
            parser.error(f"Directory path '{args.dir_path}' does not exist.")

        bib_files = glob.glob(os.path.join(args.dir_path, '*.bib'))
        if not bib_files:
            parser.error(f"No .bib files found in the specified directory '{args.dir_path}'.")

        bib_databases = [read_bib_file(infile) for infile in bib_files]

    else:
        bib_files=args.infiles
        bib_databases = [read_bib_file(infile) for infile in bib_files]


    if ((args.op == 'i' or args.op == 'd') and len(args.infiles) != 2):
        parser.error("Operation requires two input files")

    end = time.time()

    print(f"Time to read input files: {end - start} seconds")
    print(f"Found {sum(len(bib_db.entries) for bib_db in bib_databases)} entries")


    bib_databases, removed_entries = zip(*[remove_entries_without_field(bib_db, args.f[0]) for bib_db in bib_databases])
    for i, removed in enumerate(removed_entries):
        if removed:
            print(f"Ignored {len(removed)} entries from {bib_files[i]} that do not contain the field '{args.f[0]}'.")

    result_database = bibtexparser.bibdatabase.BibDatabase()

    #op with more than 2 input files
    if args.op == 'm':
        result_database = merge_bib_databases(*bib_databases, field=args.f[0])
        print(f"Merged {sum(len(bib_db.entries) for bib_db in bib_databases)} entries from {', '.join(bib_files)}. Found {(sum(len(bib_db.entries) for bib_db in bib_databases))-len(result_database.entries)} duplicates. Merging result contains {len(result_database.entries)} entries.")
    #op with 2 input files
    elif args.op == 'i':
        INTERSECtion = find_intersection(bib_databases[0], bib_databases[1], args.f[0])
        result_database.entries = intersection
        print(f"Found {len(result_database.entries)} common entries in {args.infiles[0]} and {args.infiles[1]}.")
    elif args.op == 'd':
        difference = find_difference(bib_databases[0], bib_databases[1], args.f[0])
        result_database.entries = difference
        print(f"Found {len(result_database.entries)} unique entries in {args.infiles[0]} compared to {args.infiles[1]}.")

    if args.include or args.exclude:
        #check if result_database is empty
        if not result_database.entries:
            result_database = merge_bib_databases(*bib_databases, field=args.f[0])

        filtered_entries = filter_entries_by_regex(result_database,args.f, args.include, args.exclude)
        if not filtered_entries:
            print("Filtering removed all entries.")
        else:
            print(f"After filtering, result contains {len(filtered_entries)} of {len(result_database.entries)}.")

        result_database.entries = filtered_entries

    if args.list:
        #check if result_database is empty
        if not result_database.entries:
            result_database = merge_bib_databases(*bib_databases, field=args.f[0])
    
        for entry in result_database.entries:
            for field in args.f:
                if field in entry:
                    print(entry[field])

            




    write_bib_file(args.output_file, result_database)
