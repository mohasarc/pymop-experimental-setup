import csv
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor
import os
from threading import Lock
import time

TIMEOUT_SECONDS = "3600"
PROJECTS_CSV_NAME = "project-links.csv"
ALGORITHMS = ["ORIGINAL", "B", "C", "C+", "D"]

# Get the current working directory as an absolute path
current_dir = os.getcwd()

started_containers = 0
total_containers = 0
lock = Lock()

def print_stats(link, sha, algorithms):
    """Print progress statistics"""
    global started_containers
    with lock:
        started_containers += 1
        if len(sha) > 7:
            sha = sha[:7]
        print(f"Running {started_containers}/{total_containers}: {link} with sha {sha}, algorithms {algorithms}")

def update_run_status(link, sha, algorithms, status, elapsed_time):
    """Update the status of the run in a CSV file"""
    results_file = f"{current_dir}/results/runs.csv"
    with lock:
        if len(sha) > 7:
            sha = sha[:7]
        # Read existing rows
        rows = []
        if os.path.isfile(results_file):
            with open(results_file, mode='r') as file:
                csv_reader = csv.DictReader(file)
                rows = list(csv_reader)
        
        # Check if the entry exists and update it
        updated = False
        algos = " ".join(algorithms)

        for row in rows:
            if row["link"] == link and row["sha"] == sha and row["algorithms"] == algos:
                row["status"] = status
                row["elapsed_time"] = elapsed_time
                updated = True
                break
        
        # if entry doesnot exist, add a new one
        if not updated:
            rows.append({
                "link": link,
                "sha": sha,
                "algorithms": algos,
                "status": status,
                "elapsed_time": elapsed_time
            })
        
        # Write all rows back to the file
        with open(results_file, mode='w', newline='') as file:
            csv_writer = csv.DictWriter(file, fieldnames=["link", "sha", "algorithms", "status", "elapsed_time"])
            csv_writer.writeheader()
            csv_writer.writerows(rows)
            file.flush()

def run_container(link, sha, algorithms):
    """Run a Docker container for a specific project"""
    
    print_stats(link, sha, algorithms)

    # Record start time and mark as Running
    started_at = time.time()
    status = "Running"
    update_run_status(link, sha, algorithms, status=status, elapsed_time="-1")

    try:
        args = [
            "docker", "run", 
            "--rm", 
            "-v", f"{current_dir}/results/:/experiment/__results__",
            "denini/pymop-experiment",
            "--link", link,
            "--sha", sha,
            "--timeout", TIMEOUT_SECONDS,
            "--algorithms", " ".join(algorithms)
        ]
        with lock:
            print(f"Running container with args: {args}")
        subprocess.run(args, check=True, timeout=9000) # timeout after 2.5 hours
        status = "Done"
    except subprocess.CalledProcessError as e:
        status = "Failed"
        with lock:
            print(f"Container failed with exit code {e.returncode} for {link} {sha}")
    except subprocess.TimeoutExpired:
        status = "Timeout"
        with lock:
            print(f"Container timed out for {link} {sha}")
    except Exception as e:
        status = "Exception"
        with lock:
            print(f"Error running container: {e}")
    finally:
        # Record elapsed time and update status to Done
        elapsed_time = round(time.time() - started_at, 2)
        update_run_status(link, sha, algorithms, status=status, elapsed_time=elapsed_time)

def read_csv_data(file_path):
    """Read project data from CSV file"""
    with open(file_path, mode='r') as file:
        csv_reader = csv.DictReader(file)
        entries = [{'link': row["link"], 'sha': row["sha"]} for row in csv_reader]
        print(f"Read {len(entries)} entries from {file_path}")
    return entries

def main():
    global total_containers
    # Read and prepare project data
    csv_file_path = os.path.join(current_dir, PROJECTS_CSV_NAME)
    data_entries = read_csv_data(csv_file_path)

    # Create results directory if it doesn't exist
    results_dir = os.path.join(current_dir, "results")
    os.makedirs(results_dir, exist_ok=True)

    # rm results/runs.csv if it exists
    runs_csv_path = os.path.join(results_dir, "runs.csv")
    if os.path.isfile(runs_csv_path):
        os.remove(runs_csv_path)

    # Get max concurrent containers from command line or use default
    max_workers = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    
    time_start = time.time()
    print(f'Time start: {time_start}')
    print(f"Starting execution with {max_workers} concurrent containers")
    print(f"Total projects to process: {len(data_entries)}")
    print('--' * 20 + '\n')

    # Prepare tasks
    tasks = []
    if run_all_algos_in_one_container:
        # One task per project, all algorithms in one container
        tasks = [
            (entry['link'], entry['sha'], ALGORITHMS)
            for entry in data_entries
        ]
    else:
        # One task per project-algorithm pair
        tasks = [
            (entry['link'], entry['sha'], [algorithm])
            for entry in data_entries
            for algorithm in ALGORITHMS
        ]

    total_containers = len(tasks)

    # Execute tasks using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks and get future objects
        futures = [
            executor.submit(run_container, link, sha, algorithms)
            for link, sha, algorithms in tasks
        ]
        
        # Wait for all tasks to complete
        for future in futures:
            try:
                future.result()  # This will raise any exceptions that occurred in the thread
            except Exception as e:
                print(f"Task failed with error: {e}")

    time_end = time.time()
    print("\nAll containers completed!")
    total_time = round(time_end - time_start, 2)
    print(f"Total time taken: {total_time} seconds")


if __name__ == "__main__":
    run_all_algos_in_one_container = True  # set this to False for separate containers per algorithm
    main()
