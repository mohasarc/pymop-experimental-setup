# Pymop Experiment

This is a Docker-based configuration to run pymop. Follow the steps below to get started:

1. Ensure you have Docker installed on your system.
2. Clone the repository
3. Add your GitHub token to `.env` file

   ```sh
   GITHUB_TOKEN=<your_token>
   ```

4. Build the Docker image (this might take a while)

   ```sh
   python3 ./src/build-container.py
   ```

5. Place the project links in `project-links.csv` file with the following header:

   ```csv
   link,sha
   ```

6. Run the experiment using the following command (replace `<max_concurrent_containers>` with the desired number of concurrent containers):

   ```sh
   python3 ./src/run-experiment.py <max_concurrent_containers>
   ```

That's it! The script will handle the rest. The results will be saved in the `results` directory.
While the program is running the file `results/runs.csv` will update the run status of each project/algo.

7.  To get the csv of the results you can run

        ```sh
        bash ./src/organize_output.sh
        python3 ./src/parse-reports.py
        python3 ./src/sanity_check.py
        ```

    The results will be in `sanity-check-results.csv`

8.  If you want to see the results in other format you need call the script `src/reshape.py`

    install pandas in env

    ```sh
    python3 -m venv env
    source env/bin/activate
    pip install -r requiriments.txt
    ```

    ```sh
    python3 src/reshape.py
    ```

The results will be in `algorithm_results.csv`
