import csv
import json
import sys

csv.field_size_limit(sys.maxsize)


def read_csv_to_list_dict(file_name):
    with open(file_name) as file:
        reader = csv.DictReader(file)
        return list(reader)

def find_missing_required_algo(project_lines, name, required_algos):
    # return an array of the missing required algorithm
    missing = []
    for algo in required_algos:
        found = False
        for line in project_lines:
            if line['algorithm'] == algo:
                found = True
                break
        if not found:
            missing.append(algo)
    return missing


def is_results_diff(lines, name):
    columns = ['passed', 'failed']
    # check if the diffs are the same for all lines for all columns
    for c in columns:
        results = set()
        for l in lines:
            # check if the value is a number using int
            try:
                if l[c] == '':
                    l[c] = 0
                if c == 'passed' and int(l[c]) == 0: # the project should have at least 1 passed test
                    print(f'***Project {name} has 0 passed tests')
                    return True
                results.add(int(l[c]))
            except:
                print(f'***Project {name} has non-integer {c} value')
                return True

            if len(results) != 1:
                print(f'!!!Project {name} has different {c} values. Algorithm: {l["algorithm"]}')
                return True
    return False


def sanity_check(lines):
    # lopp through all lines, create a dict by project and add the lines to the dict
    projects = {}
    successful_projects = {}

    problems = 0
    problems_memory = 0
    problems_diff_values = 0

    REQUIRED_ALGOS = [
        'ORIGINAL',
        # 'A',
        'B',
        'C',
        'C+',
        'D'
    ]

    original_keys = lines[0].keys()

    for l in lines:
        project = l["project"]
        if project not in projects:
            projects[project] = []
        projects[project].append(l)

    del lines

    # check if all projects have 6 lines
    for p in projects:
        missing_required_algos = find_missing_required_algo(projects[p], p, REQUIRED_ALGOS)

        if len(missing_required_algos) > 0:
            problems += 1
            print('---')
            found_algos = []

            for line in projects[p]:
                found_algos.append(line['algorithm'])

            print(f"Project {p} did not run on all required algos. Required: {REQUIRED_ALGOS}. Found: {found_algos}. Missing: {missing_required_algos}")
        else:
            # for line in projects[p]:
            #     mem = line['memory']
            #     if mem in [None, '', ' '] or float(mem) == 0:
            #         line['memory'] = 1
            #         problems_memory += 1
            #     elif float(mem) < 0:
            #         line['memory'] = float(mem) * -1

            if not is_results_diff(projects[p], p):
                # add the project to the new dict
                successful_projects[p] = projects[p]
            else:
                problems_diff_values += 1

    print(
        f"num of problems related to number of lines: {problems} (skip these projects)")
    print(
        f"num of problems related to memory: {problems_memory} (we add value 1)")
    print(
        f"num of problems related to different values across columns of the same project: {problems_diff_values} (skip these projects)")

    print(f'total input projects: {len(projects)}')
    print(f'total projects output: {len(successful_projects)}')

    print(
        f"saving new csv, with only projects that successfully ran algos {REQUIRED_ALGOS} ")

    file_name = 'sanity-check-results.csv'
    successful_projects = update_test_duration(successful_projects)
    save_new_csv(file_name, successful_projects, original_keys)
    print("saved new csv, file name: sanity-check-results.csv")


def update_test_duration(lines):
    for p in lines:
        for l in lines[p]:

            l['old_test_duration'] = l['test_duration']
            
            if l['algorithm'] == 'ORIGINAL':
                l['test_duration'] = l['time']
            
            else:
                t = float(l['time'] or 0)
                t_i = float(l['time_instrumentation'] or 0)
                # t_c_m = float(l['time_create_monitor'] or 0)
                l['test_duration'] = round(t + t_i, 2)
    return lines

def save_new_csv(file_name, new_projects, original_keys):
    new_keys = list(original_keys)
    new_keys.append('old_test_duration')
    original_keys = new_keys
    
    with open(file_name, mode='w') as file:
        fieldnames = original_keys
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for p in new_projects:
            for line in new_projects[p]:
                if line['project'].startswith('results/'):
                    line['project'] = line['project'].replace('results/', '')
                writer.writerow(line)


def main():
    lines = read_csv_to_list_dict("results/results.csv")
    sanity_check(lines)


main()