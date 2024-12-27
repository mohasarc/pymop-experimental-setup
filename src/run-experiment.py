import csv
import subprocess
from concurrent.futures import ThreadPoolExecutor
import os
from threading import Lock
import time

TIMEOUT_SECONDS = "14400"
PROJECTS_CSV_NAME = "project-links.csv"

with open('./.env', 'r') as file:
    GITHUB_TOKEN = file.read().strip().split('=')[1]

# Get the current working directory as an absolute path
current_dir = os.getcwd()

started_containers = 0
total_time = 0
lock = Lock()

def print_stats(total_containers, link, sha):
    """Print progress statistics"""
    print(f"Running {started_containers}/{total_containers}: {link} with sha {sha} with timeout {TIMEOUT_SECONDS}")
    print('\n')
    print(f"Total time: {total_time} seconds")
    print(f"Average time per container: {total_time / started_containers} seconds")
    print(f"Estimated remaining time: {(total_time / started_containers) * (total_containers - started_containers)} seconds")
    print('\n')

def run_container(link, sha, total_containers):
    """Run a Docker container for a specific project"""
    global started_containers
    with lock:
        started_containers += 1
        print_stats(total_containers, link, sha)

    started_at = time.time()
    try:
        subprocess.run([
            "docker", "run", 
            "--rm", 
            "-v", f"{current_dir}/results/:/experiment/__results__",
            "pymop-experiment",
            link,
            sha,
            TIMEOUT_SECONDS,
            GITHUB_TOKEN
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Container failed with exit code {e.returncode} for {link} {sha}")
    except Exception as e:
        print(f"Error running container: {e}")

    ended_at = time.time()
    with lock:
        global total_time
        total_time += ended_at - started_at

def read_csv_data(file_path):
    """Read project data from CSV file"""
    with open(file_path, mode='r') as file:
        csv_reader = csv.DictReader(file)
        entries = [{'link': row["link"], 'sha': row["sha"]} for row in csv_reader]
    return entries

def main():
    # Read and prepare project data
    csv_file_path = os.path.join(current_dir, PROJECTS_CSV_NAME)
    data_entries = read_csv_data(csv_file_path)

    # Create results directory if it doesn't exist
    results_dir = os.path.join(current_dir, "results")
    os.makedirs(results_dir, exist_ok=True)

    # Get max concurrent containers from command line or use default
    import sys
    if len(sys.argv) > 1:
        max_workers = int(sys.argv[1])
    else:
        max_workers = 3

    print(f"Starting execution with {max_workers} concurrent containers")
    print(f"Total projects to process: {len(data_entries)}")

    # Run Docker containers concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(
            lambda entry: run_container(
                entry['link'], 
                entry['sha'], 
                len(data_entries)
            ), 
            data_entries
        )

    print("\nAll containers completed!")
    print(f"Total execution time: {total_time} seconds")
    print(f"Average time per project: {total_time / len(data_entries)} seconds")

if __name__ == "__main__":
    main()