import csv
import subprocess
from concurrent.futures import ThreadPoolExecutor
import os
from threading import Lock
import time

ALGOS = ['original', 'A', 'B', 'C', 'C+', 'D']
PROJECTS_CSV_NAME = "project-links.csv"
TIMEOUT_SECONDS = "14400"

with open('./.env', 'r') as file:
    GITHUB_TOKEN = file.read().strip().split('=')[1]

# Get the current working directory as an absolute path
current_dir = os.getcwd()

started_containers = 0
total_time = 0
lock = Lock()

def print_stats(total_containers, link, sha, algo):
    print(f"Running {started_containers}/{total_containers}: {link} with sha {sha} and algo {algo} with timeout {TIMEOUT_SECONDS}")
    print('\n')
    print(f"Total time: {total_time} seconds")
    print(f"Average time per container: {total_time / started_containers} seconds")
    print(f"Estimated remaining time: {(total_time / started_containers) * (total_containers - started_containers)} seconds")
    print('\n')

# Function to run the Docker container with link and sha as arguments
def run_container(link, sha, algo, total_containers):
    global started_containers
    with lock:
        started_containers += 1
        print_stats(total_containers, link, sha, algo)

    started_at = time.time()

    project_name = link.split('/')[-1].replace('.git', '')
    unique_results_dir = f"{current_dir}/results/{project_name}_{sha}_{algo}/"
    try:
        subprocess.run([
            "docker", "run", "--rm", "-v", f"{unique_results_dir}:/experiment/__results__", "pymop-experiment", link, sha, algo, TIMEOUT_SECONDS, GITHUB_TOKEN
        ])
    except Exception as e:
        print(f"Error running container: {e}")

    ended_at = time.time()
    with lock:
        global total_time
        total_time += ended_at - started_at

# Read data from the CSV file
def read_csv_data(file_path):
    with open(file_path, mode='r') as file:
        csv_reader = csv.DictReader(file)
        entries = [{'link': row["link"], 'sha': row["sha"]} for row in csv_reader]
    return entries

# Main execution
csv_file_path = os.path.join(current_dir, PROJECTS_CSV_NAME)
data_entries = read_csv_data(csv_file_path)

projects_and_algos = [
    {
        'link': project['link'],
        'sha': project['sha'],
        'algo': algo
    } for project in data_entries for algo in ALGOS
]

import sys

if len(sys.argv) > 1:
    m = int(sys.argv[1])  # Max number of concurrent containers from arguments
else:
    m = 3  # Default value if not provided

# Run Docker containers concurrently with link and sha as input
with ThreadPoolExecutor(max_workers=m) as executor:
    executor.map(lambda entry: run_container(entry['link'], entry['sha'], entry['algo'], len(projects_and_algos)), projects_and_algos)
