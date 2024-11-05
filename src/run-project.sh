#!/bin/sh

echo "Running project..."

link=$1
sha=$2
algo=$3
timeout=$4
github_token=$5

# Check if all required inputs are provided
if [ -z "$link" ] || [ -z "$sha" ] || [ -z "$algo" ] || [ -z "$github_token" ] || [ -z "$timeout" ]; then
  echo "Error: Missing required arguments."
  echo "Usage: $0 <link> <sha> <algo> <github_token> <timeout>"
  exit 1
fi

########################################################
#                     CLONE REPO                       #
########################################################
echo "Cloning repository..."

retry_count=0
max_retries=10
while [ $retry_count -lt $max_retries ]; do
  git clone --depth 1 $link && break
  retry_count=$((retry_count + 1))
  echo "Clone failed. Retrying in 10 seconds... ($retry_count/$max_retries)"
  sleep 10
done

if [ $retry_count -eq $max_retries ]; then
  echo "Error: Failed to clone repository after $max_retries attempts."
  exit 1
fi

cd $(basename "$link" .git)

# checkout the sha
# If sha is not empty, attempt to checkout the sha
if [ -n "$sha" ]; then
  echo "SHA exists: $sha"
  # Assuming you have already cloned the repo and are in the repo directory
  git fetch origin "$sha" --depth 1
  git checkout "$sha"
else
  echo "SHA is empty, no checkout performed."
fi


########################################################
#                 INSTALL DEPENDENCIES                 #
########################################################
echo "Installing dependencies..."

# Create and activate a virtual environment
python3 -m venv venv
. venv/bin/activate

if [ "$algo" != "ORIGINAL" ]; then
    # clone and install pymop if algo is original
    echo "Installing pymop from pre-installed dependencies..."
    
    # Copy pre-installed packages from the permanent venv to the current one
    cp -r /opt/pymop_venv/lib/python3*/site-packages/* venv/lib/python3*/site-packages/
    
    # Create symlink to the specs directory for easy access
    ln -s /opt/mop-with-dynapt/specs-new specs-new

    # delete some problematic specs
    rm ./specs-new/TfFunction_NoSideEffect.py
    # rm ./specs-new/Sets_Comparable.py
    # rm ./specs-new/Console_CloseReader.py
    # rm ./specs-new/UnsafeMapIterator.py
    # rm ./specs-new/UnsafeListIterator.py
    # rm ./specs-new/Pydocs_UselessFileOpen.py
fi

# Install dependencies
pip3 install .[dev,test,tests,testing]

# Install additional requirements if available (within root + 2 nest levels excluding env/ folder)
find . -maxdepth 3 -type d -name "env" -prune -o -type f -name "*.txt" -print | while read -r file; do
    if [ -f "$file" ]; then
        echo "Installing requirements from $file"
        pip3 install -r "$file"
    fi
done

# Install pytest and a few common plugins
pip3 install pytest
pip3 install pytest-json-report memray pytest-memray pytest-cov pytest-env pytest-rerunfailures pytest-socket pytest-django py-spy


########################################################
#                    RUN EXPERIMENT                    #
########################################################
echo "Running experiment..."

owner=$(basename $(dirname "$link"))
repo=$(basename "$link" .git)
full_project_name="$owner-$repo-$sha-$algo"
results_dir="../$full_project_name"

if [ ! -d "$results_dir" ]; then
    mkdir "$results_dir"
fi

# save git info
sha=$(git rev-parse HEAD | cut -c1-7)
url=$(git remote get-url origin)
echo "{\"sha-commit\": \"$sha\", \"project-url\": \"$url\"}" > $results_dir/project_info.json


rm -f .pymon

echo ============= Specs being used are =============
if [ -d "$PWD"/specs-new/ ]; then
    ls -al "$PWD"/specs-new/
fi
echo ================================================ 

set -x
export PYTHONIOENCODING=utf8

START_TIME=$(python3 -c 'import time; print(time.time())')
echo "START_TIME: $START_TIME"
if [ "$algo" = "ORIGINAL" ]; then
    # Run without pythonmop
    timeout $timeout py-spy record -i -o $algo-profile-flamegraph.svg -r 100 -s --function -d $((timeout - 10)) -- pytest \
        --color=no \
        -v \
        -rA \
        --memray \
        --trace-python-allocators \
        --most-allocations=0 \
        --memray-bin-path=$results_dir/MEM_$algo \
        --continue-on-collection-errors \
        --json-report \
        --json-report-indent=2 > $results_dir/$algo-pytest-output.txt 2>&1  # Redirecting pytest output to a file
else
    timeout $timeout py-spy record -i -o $algo-profile-flamegraph.svg -r 100 -s --function -d $((timeout - 10)) -- pytest \
        --color=no \
        -v \
        -p pythonmop \
        -rA \
        --path="$PWD"/specs-new/ \
        --algo $algo \
        --memray \
        --trace-python-allocators \
        --most-allocations=0 \
        --memray-bin-path=$results_dir/MEM_$algo \
        --continue-on-collection-errors \
        --json-report \
        --json-report-indent=2 \
        --statistics \
        --statistics_file="$algo".json > $results_dir/$algo-pytest-output.txt 2>&1
fi

END_TIME=$(python3 -c 'import time; print(time.time())')
echo "END_TIME: $END_TIME"
END_TO_END_TIME=$(python3 -c "print($END_TIME - $START_TIME)")
echo "END_TO_END_TIME: $END_TO_END_TIME"
echo "{\"test_duration\": ${END_TO_END_TIME}}" > $results_dir/$algo-e2e-time.json

# Check if the last command exited with a status code of 124, which indicates a timeout
if [ $? -eq 124 ]; then
    echo "PROJECT TIMEOUT: ALGO_$algo" > $results_dir/TIMEOUT-output_$algo.txt
fi

set +x
    
ls -l

mv .report.json $results_dir/$algo.report.json
mv "$algo"-full.json $results_dir/$algo-full.json
mv "$algo"-violations.json $results_dir/$algo-violations.json
mv "$algo"-time.json $results_dir/$algo-time.json
mv $algo-profile-flamegraph.svg $results_dir/$algo-profile-flamegraph.svg


ls -l $results_dir

########################################################
#                      SAVE RESULTS                    #
########################################################

# Zip file name: owner-repo-algo-sha.zip
zip_file="../__results__/$full_project_name.tar.gz"

# compress results dir
tar -czvf $zip_file $results_dir

# No need to perform cleanup as this will run in a Docker container
# deactivate
# cd ..
# rm -rf $(basename "$link" .git)
# rm -rf venv
# rm -rf mop-with-dynapt
