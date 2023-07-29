import argparse
import bibtexparser
#import bib_functions
import time
import re

def read_bib_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as bibfile:
        return bibtexparser.load(bibfile)

def convert_field_to_lower(bib_database, field):
    for entry in bib_database.entries:
        if field in entry:
            entry[field] = entry[field].lower()
    return bib_database

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
            if field in entry and entry[field] not in merged_set:
                merged_bib_database.entries.append(entry)
                merged_set.add(entry[field])
    return merged_bib_database


def find_intersection(bib_database1, bib_database2, field):
    intersection = []
    entries_set = {entry[field] for entry in bib_database1.entries}
    for entry in bib_database2.entries:
        if entry[field] in entries_set:
            intersection.append(entry)
    return intersection

#def find_intersection(bib_database1, bib_database2, field):
#    # Convert Python dictionaries to a list of BibEntry objects
#    bib_entries1 = [bib_functions.BibEntry(str(entry[field]), i,True) for i, entry in enumerate(bib_database1.entries)]
#
#    bib_entries2 = [bib_functions.BibEntry(str(entry[field]), i,False) for i, entry in enumerate(bib_database2.entries)]
#
#    # Call the C++ function using the Python bindings
#    intersection = bib_functions.find_intersection(bib_entries1, bib_entries2)
#
#    # Convert the result back to Python dictionaries
#    intersection_entries = [bib_database1.entries[entry._id] if entry._first else bib_database2.entries[entry._id] for entry in intersection]
#    return intersection_entries

def find_difference(bib_database1, bib_database2, field):
    difference = []
    entries_set = {entry[field] for entry in bib_database2.entries}
    for entry in bib_database1.entries:
        if entry[field] not in entries_set:
            difference.append(entry)
    return difference

def write_bib_file(file_path, bib_database):
    with open(file_path, 'w', encoding='utf-8') as bibfile:
        bibtexparser.dump(bib_database, bibfile)

def remove_duplicates(bib_database, duplicates):
    unique_entries = [entry for entry in bib_database.entries if entry not in duplicates]
    unique_bib_database = bibtexparser.bibdatabase.BibDatabase()
    unique_bib_database.entries = unique_entries
    return unique_bib_database

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
    parser.add_argument('-include', default='', help='Regex expression for inclusion')
    parser.add_argument('-exclude', default='', help='Regex expression for exclusion')
    parser.add_argument('-op',required=False, choices=['m', 'd', 'i'], help='Choose m for merge, d for difference or i for intersection')
    parser.add_argument('-l', required=False,default='0', help='Tranform specified fields to lower case (default disabled)')
    parser.add_argument('-in',required=True, nargs='+',dest="infiles", help='List of .bib input files')
    parser.add_argument('-out',required=True,dest='output_file', help='Output .bib file name or threshold percentage')
    args = parser.parse_args()

    if ((args.op == 'i' or args.op == 'd') and len(args.infiles) != 2):
        parser.error("Operation requires two input files")


    start = time.time()
    bib_databases = [read_bib_file(infile) for infile in args.infiles]
    end = time.time()
    print(f"Time to read input files: {end - start} seconds")
    print(f"Found {sum(len(bib_db.entries) for bib_db in bib_databases)} entries")

    if args.l == '1':
        for bib_database in bib_databases:
            bib_database = convert_field_to_lower(bib_database, args.f[0])


    bib_databases, removed_entries = zip(*[remove_entries_without_field(bib_db, args.f[0]) for bib_db in bib_databases])
    for i, removed in enumerate(removed_entries):
        if removed:
            print(f"Ignored {len(removed)} entries from {args.infiles[i]} that do not contain the field '{args.f[0]}'.")

    result_database = bibtexparser.bibdatabase.BibDatabase()

    #op with more than 2 input files
    if args.op == 'm':
        result_database = merge_bib_databases(*bib_databases, field=args.f[0])
        print(f"Merged {sum(len(bib_db.entries) for bib_db in bib_databases)} entries from {', '.join(args.infiles)}. Found {(sum(len(bib_db.entries) for bib_db in bib_databases))-len(result_database.entries)} duplicates. Merging result contains {len(result_database.entries)} entries.")
    #op with 2 input files
    elif args.op == 'i':
        intersection = find_intersection(bib_databases[0], bib_databases[1], args.f[0])
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


    write_bib_file(args.output_file, result_database)
