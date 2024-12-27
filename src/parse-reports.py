import os
import json
import subprocess
from collections import OrderedDict
from collections import Counter
import re
import csv

SQL_QUERY_MEM = 'SELECT t.RUN_DESCRIPTION, AVG(m.MEM_USAGE) AS average_memory_usage FROM TEST_METRICS m JOIN TEST_SESSIONS t ON m.SESSION_H = t.SESSION_H GROUP BY t.SESSION_H;'
SQL_QUERY_TIME2 = 'SELECT t.RUN_DESCRIPTION, SUM(m.USER_TIME) AS total_user_time FROM TEST_METRICS m JOIN TEST_SESSIONS t ON m.SESSION_H = t.SESSION_H GROUP BY t.SESSION_H;'
problems = {}
NUM_ALGORITHMS = 6
REGEX_MEMORY_FILE = re.compile(r"Total memory allocated: (\d+\.?\d*)([a-zA-Z]+)")

def convert_to_bytes(value, unit):
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
        'KiB': 1024,
        'MiB': 1024 ** 2,
        'GiB': 1024 ** 3,
        'TiB': 1024 ** 4,
    }
    return value * units[unit]


def process_memory_file(file_path):
    total_memory_bytes = 0
    regex = REGEX_MEMORY_FILE

    with open(file_path, 'r') as file:
        for line in file:
            match = regex.search(line)
            if match:
                value = float(match.group(1))
                unit = match.group(2)

                # convert to bytes
                total_memory_bytes += convert_to_bytes(value, unit)

    return total_memory_bytes


def get_time_from_json(projectname, algorithm):
    filename = f'{algorithm}-time.json'
    # check filename
    if not os.path.isfile(filename):
        add_problem(projectname, algorithm, "json time not found")
        return None
    # read json file
    with open(filename, 'r') as f:
        json_data = json.load(f)

    # example json_data:
    # {
    # "instrumentation_duration": 0.0006315708160400391,
    # "create_monitor_duration": 0.0004477500915527344,
    # "test_duration": 0.425640344619751
    # }
    #
    #
    try:
        instrumentation_duration = json_data['instrumentation_duration']
    except:
        instrumentation_duration = 0

    try:
        create_monitor_duration = json_data['create_monitor_duration']
    except:
        create_monitor_duration = 0

    try:
        test_duration = json_data['test_duration']
    except:
        test_duration = 0

    return instrumentation_duration, create_monitor_duration, test_duration


def get_monitors_and_events_from_json(projectname, algorithm):
    filename = f'{algorithm}-full.json'
    # check filename
    if not os.path.isfile(filename):
        add_problem(projectname, algorithm, "json full not found")
        return None
    # read json file
    with open(filename, 'r') as f:
        json_data = json.load(f)

    # example of json
    '''
    {
    "Thread_StartOnce": {
        "monitors": 0,
        "events": {
        "start": 2
        }
    }
    }
    '''
    return_str_monitors = ""
    return_str_events = ""
    total_monitors = 0
    total_events = 0

    for spec in json_data.keys():
        num_monitors = json_data[spec]["monitors"]
        toal_events = sum(json_data[spec]["events"].values())
        return_str_monitors += f'{spec}={num_monitors}<>'
        for event in json_data[spec]["events"].keys():
            return_str_events += f'{spec}={event}={json_data[spec]["events"][event]}<>'
        total_monitors += num_monitors
        total_events += toal_events

    return return_str_monitors[:-1], return_str_events[:-1], total_monitors, total_events

    return return_string[:-1], total_violations


def get_num_violations_from_json(projectname, algorithm):
    filename = f'{algorithm}-violations.json'
    # check filename
    if not os.path.isfile(filename):
        add_problem(projectname, algorithm, "json violations not found")
        return None
    # read json file
    with open(filename, 'r') as f:
        json_data = json.load(f)

    return_spec_string = ""
    total_violations = 0
    unique_violations_count = ""
    unique_violations_summary = {}
    unique_violations_test = {}

    for spec in json_data.keys():
        size = len(json_data[spec])
        return_spec_string += f'{spec}={size};'

        # Count unique elements and their occurrences
        violations = []
        violations_test = {}
        for item in json_data[spec]:
            violations += [item['violation']]
            if violations_test.get(item['violation']) is None:
                violations_test[item['violation']] = set()
            violations_test[item['violation']].add(item['test'])
        violations_counter = Counter(violations)

        # Store the unique violation counts and summary in the dictionaries
        unique_violations_summary[spec] = dict(violations_counter)
        unique_violations_test[spec] = dict(violations_test)
        unique_violations_count += f'{spec}={len(dict(violations_counter))};'

        total_violations += size

    return (return_spec_string[:-1], total_violations, unique_violations_count, unique_violations_summary,
            unique_violations_test)


def get_result_line(filename):
    # get last line from file
    try:
        last_line = subprocess.check_output(
            ['tail', '-1', filename]).decode('utf-8').strip()
        # if the last line is not the one we want, get the last 100 lines and search
        if 'in' in last_line and re.search(r'\b(passed|errors|error)\b', last_line) and "WARNING" not in last_line:
            return last_line
        else:
            last_lines = subprocess.check_output(
                ['tail', '-500', filename]).decode('utf-8').strip().split('\n')
            for line in reversed(last_lines):
                if 'in' in line and re.search(r'\b(passed|errors|error)\b', line) and "WARNING" not in line:
                    last_line = line
                    return last_line
            
    except:
        return None

def find_problems(filename):
    # look for keywords like fatal, sigmentation fault, core dump within the data in filename and return the line containing the error as well as 5 lines above and 10 after
    try:
        lines = subprocess.check_output(
            ['grep', '-A', '10', '-B', '5', '-i', '-E', 'fatal|segmentation fault|core dump', filename]).decode('utf-8').strip().split('\n')
        return lines
    except:
        return None

def get_results(filename, project, algorithm):
    # check filename
    if not os.path.isfile(filename):
        add_problem(project, algorithm, "File not found")
        raise Exception('File not found', filename)

    last_line = get_result_line(filename)
    print('--->last_line->', last_line)
    try:
        time = last_line.split('in ')[1].split('s')[0].strip()
    except Exception as e:
        add_problem(project, algorithm,f"Error parsing time. last_line={last_line}")
        raise Exception(f'Error parsing time. last_line={last_line}. Original Error: {e}')

    line = OrderedDict({
        'project': project,
        'algorithm': algorithm,
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'xfailed': 0,
        'xpassed': 0,
        'errors': 0,
        'time': time,
        'execution_problems': ''
    })

    for att in last_line.split(','):
        for attribute in line.keys():
            attr = f' {attribute}'
            if attr in att:
                # get only the number
                num = att.split(' ')[1].strip()
                # check if it is a number
                try:
                    int(num)
                except Exception as e:
                    num = att.split(' ')[0].strip()
                line[attribute] = num
                break

    return line


def get_memory_from_db(projectname, algorithm):
    # run sqlite3 db.pymon < test.sql and get the output
    try:
        output_lines = subprocess.check_output(
            ['sqlite3', f'db.pymon_{algorithm}', SQL_QUERY_MEM], stderr=subprocess.DEVNULL).decode('utf-8').strip().split('\n')
    except Exception as e:
        print('Failed to run SQL query', e)
        print('directory contents:')
        print(os.listdir())
        add_problem(projectname, algorithm, f"Error running SQL query.")
        return 0.0

    algo = f'"ALGO_{algorithm}"'

    if len(output_lines) == 0:
        add_problem(projectname, algorithm, "No data in database")
    if len(output_lines) > NUM_ALGORITHMS:
        add_problem(projectname, algorithm,
                    f"Too many lines in database. len={len(output_lines)}")
        return 0.0

    for line in output_lines:
        if algo in line:
            average = line.split('|')[1].strip()
            return round(float(average), 2)


def get_time_from_db(projectname, algorithm):
    # run sqlite3 db.pymon < test.sql and get the output
    try:
        output_lines = subprocess.check_output(
            ['sqlite3', f'db.pymon_{algorithm}', SQL_QUERY_TIME2], stderr=subprocess.DEVNULL).decode('utf-8').strip().split('\n')
    except Exception as e:
        print('Failed to run SQL query', e)
        print('directory contents:')
        print(os.listdir())
        add_problem(projectname, algorithm, f"Error running SQL query.")
        return 0.0

    algo = f'"ALGO_{algorithm}"'

    if len(output_lines) == 0:
        add_problem(projectname, algorithm, "No data in database")
        return None
    if len(output_lines) > NUM_ALGORITHMS:
        add_problem(projectname, algorithm,
                    f"Too many lines in database. len={len(output_lines)}")
        return 0.0

    for line in output_lines:
        if algo in line:
            time2 = line.split('|')[1].strip()
            return round(float(time2), 2)


def compare(results, projectname):
    # Regular expression to remove ANSI escape sequences
    ansi_escape = re.compile(r'\x1b\[([0-9]+)(;[0-9]+)*m')

    # check if the columns: passed, failed, skipped, xfailed, xpassed, errors are different from the original
    original = results[0]
    keys = ['failed', 'skipped', 'xfailed', 'xpassed', 'errors']
    for key in keys:
        for result in results[1:]:
            # Ensure values are strings before attempting to strip ANSI codes
            original_value = str(original.get(key, ''))
            result_value = str(result.get(key, ''))

            # Remove ANSI escape sequences
            original_value_clean = ansi_escape.sub('', original_value)
            result_value_clean = ansi_escape.sub('', result_value)

            # Check if values are numeric before converting to integer
            if original_value_clean.isdigit() and result_value_clean.isdigit():
                diff = int(original_value_clean) - int(result_value_clean)
                if diff != 0:
                    message = f'DIFF: {key} is different from ORIGINAL. diff={diff}'
                    result['comparison_problems'] = f'{message}'
                    add_problem(projectname, result['algorithm'], message)
            else:
                message = f'Non-numeric or invalid data for comparison. Original: {original_value_clean}, Result: {result_value_clean}'
                result['comparison_problems'] = f'{message}'
                add_problem(projectname, result['algorithm'], message)
    print('done comparing')


def add_problem(project, algorithm, message):
    global problems
    if project not in problems:
        problems[project] = {}
    if algorithm not in problems[project]:
        problems[project][algorithm] = []

    problems[project][algorithm].append(message)


def print_results_csv(lines):
    # print header
    index = 0 if len(lines) == 0 else 1
    headerline = ''.join([f'{key},' for key in lines[index].keys()])
    print(headerline[:-1])

    for line in lines:
        line = ''.join([f'{value},' for value in line.values()])
        print(line[:-1])


def results_csv_file(lines):
    if not lines:
        print('No data to write.')
        return
    
    print('FILESSSSSS')
    for line in lines:
        print(line['project'], line['algorithm'])

    # Find the line with the maximum number of keys (columns)
    max_columns_line = max(lines, key=lambda line: len(line.keys()))

    with open('results.csv', 'w', newline='', encoding='utf-8') as f:
        # Use the keys from the line with the most keys as fieldnames
        writer = csv.DictWriter(f, fieldnames=max_columns_line.keys())
        writer.writeheader()
        for line in lines:
            try:
                writer.writerow(line)
                # print('success writing line:', line.keys())
            except Exception as e:
                print('could not write line:', line.keys(), str(e))

    print('CSV file created successfully.')


def print_problems_csv(problems):
    # sort keys
    problems = OrderedDict(sorted(problems.items()))
    only_diff_errors = []
    other_errors = []
    # print header
    headerline = 'project,algorithm,problem'
    print(headerline)

    for project in problems.keys():
        for algorithm in problems[project].keys():
            for problem in problems[project][algorithm]:
                line = f'{project},{algorithm},{problem}'
                # print(line)
                if 'diff' in problem:
                    only_diff_errors.append(line)
                else:
                    other_errors.append(line)

    print("\n====== ONLY DIFF ERRORS ======\n")
    for line in only_diff_errors:
        print(line)
    print("\n====== OTHER ERRORS ======\n")
    for line in other_errors:
        print(line)


def print_problems_json(problems):
    # sort keys
    problems = OrderedDict(sorted(problems.items()))
    print(json.dumps(problems, indent=2))
    type_problems = OrderedDict()
    for project in problems.keys():
        for algorithm in problems[project].keys():
            for problem in problems[project][algorithm]:
                if problem not in type_problems:
                    type_problems[problem] = 0
                type_problems[problem] += 1
    print("\n====== PROBLEMS TYPE JSON ======\n")
    print(json.dumps(type_problems, indent=2))


def main():
    global problems
    lines = []

    actual_dir = os.getcwd()

    for project in sorted(os.listdir('results')):
        # change to actual_dir
        os.chdir(actual_dir)
        project = os.path.join('results', project)
        print('!!!!',project)
        print('!!!!',os.path.isdir(project))
        print('!!!!', 'report' not in project)
        if os.path.isdir(project) and 'report' not in project:
            # Remove the trailing slash to get the project name
            projectname = project.rstrip('/')
            print("======")
            print(f'Project: {projectname}')

            os.chdir(projectname)
            print("directory contents:", os.listdir())

            # Iterate through each algorithm
            algos = ["ORIGINAL", "A", "B", "C", "C+", "D"]
            results = []

            for algorithm in algos:
                print(f'Algo: {algorithm}')
                filename = f'{algorithm}-pytest-output.txt'
                line = None
                try:
                    line = get_results(filename, projectname, algorithm)
                except Exception as e:
                    line = {
                        'project': project,
                        'algorithm': algorithm,
                        'execution_problems': f'{e}'
                    }

                more_problems = find_problems(filename)
                if more_problems:
                    line['execution_problems'] = f'{line["execution_problems"]}\n\n{more_problems}'

                if not 'File not found' in line['execution_problems']:

                    # get the memory from the output file
                    try:
                        total_memory_bytes = process_memory_file(filename)
                        total_memory_kb = round(total_memory_bytes / 1024, 2)
                    except Exception as e:
                        line['execution_problems'] = f'{line["execution_problems"]}\n\nCould not process_memory_file. Original error: {e}'
                        total_memory_kb = None

                    line['usage_memory'] = total_memory_kb

                    # get time from json produced by pymop
                    try:
                        print('here')
                        ret_time = get_time_from_json(projectname, algorithm)
                        print(f'ret_time: {ret_time}')
                    except Exception as e:
                        line['execution_problems'] = f'{line["execution_problems"]}\n\nCould not get_time_from_json. Original error: {e}'
                        ret_time = None

                    if ret_time is not None:
                        (instrumentation_duration,
                         create_monitor_duration, test_duration) = ret_time
                        line['time_instrumentation'] = instrumentation_duration
                        line['time_create_monitor'] = create_monitor_duration
                        line['test_duration'] = test_duration

                    # get time2 from db
                    # time2 = get_time_from_db(projectname, algorithm)
                    # line['time2'] = time2

                    # get memory from db
                    # mem = get_memory_from_db(projectname, algorithm)
                    # line['memory'] = mem

                    if algorithm != "ORIGINAL":

                        # get violations from json
                        ret_violation = get_num_violations_from_json(projectname, algorithm)
                        print(f'here2')

                        if ret_violation is not None:
                            (
                                violations_str,
                                total_violations,
                                unique_violations_count,
                                unique_violations_summary,
                                unique_violations_test
                            ) = (
                                ret_violation[0],
                                ret_violation[1],
                                ret_violation[2],
                                ret_violation[3],
                                ret_violation[4]
                            )
                            print('here3')
                            line['total_violations'] = total_violations
                            line['violations'] = violations_str
                            line['unique_violations_count'] = unique_violations_count
                            str_unique_violations_summary = str(unique_violations_summary).replace(",", "<>")
                            line['unique_violations_summary'] = str_unique_violations_summary
                            str_unique_violations_test = str(unique_violations_test).replace(",", "<>")
                            line['unique_violations_test'] = str_unique_violations_test

                        print('here4')
                        # get monitors and events from json
                        ret_full = get_monitors_and_events_from_json(projectname, algorithm)

                        if ret_full is not None:
                            monitors_str, events_str, total_monitors, total_events = ret_full[0], ret_full[1], ret_full[2], ret_full[3]

                            line['monitors'] = monitors_str
                            line['total_monitors'] = total_monitors
                            line['events'] = events_str
                            line['total_events'] = total_events                    

                    # check if log_link.txt exists
                    if os.path.isfile('logs_link.txt'):
                        with open('logs_link.txt', 'r') as file:
                            log_file = file.read()

                            # replace the last part of log_file from _(.+).zip to _{algorithm}.zip
                            log_file = re.sub(r'_([A-Z]+).zip', f'_{algorithm}.zip', log_file)

                            line['log_file'] = log_file
                    print('here5')
                    results.append(line)
            if len(results) == 0:
                print(f'No results found for {projectname}')
                os.chdir('..')
                continue
            compare(results, project)
            print('here6')
            lines.extend(results)
            print(f'LEN LINES: {len(lines)}')

            os.chdir('..')
            print("======")
        else:
            print('else')

    print("\n====== RESULTS CSV ======\n")
    # print_results_csv(lines)
    results_csv_file(lines)
    print('created results.csv')
    print("\n====== PROBLEMS CSV ======\n")
    print_problems_csv(problems)
    print("\n====== PROBLEMS JSON ======\n")
    # print_problems_json(problems)


main()