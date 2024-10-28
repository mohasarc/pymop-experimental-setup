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

git clone --depth 1 $link

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
python -m venv venv
source venv/bin/activate

# Install dependencies
pip3 install .[dev,test,tests,testing]

# Install additional requirements if available (within root + 2 nest levels excluding env/ folder)
find . -maxdepth 3 -type d -name "env" -prune -o -type f -name "*.txt" -print | while read -r file; do
    if [ -f "$file" ]; then
        pip3 install -r "$file"
    fi
done

# Install pytest and a few common plugins
pip install pytest
pip install pytest-json-report memray pytest-memray pytest-cov pytest-env pytest-rerunfailures pytest-socket pytest-django

if [ "$algo" != "original" ]; then
    # clone and install pymop if algo is original
    echo clonning and installing pymop

    cd ..


    git clone https://${github_token}@github.com/SoftEngResearch/mop-with-dynapt.git
    cd mop-with-dynapt
    git checkout add_statistics_new

    pip install .
    sudo apt-get install python3-tk -y

    # delete some problematic specs
    rm ./specs-new/TfFunction_NoSideEffect.py
    rm ./specs-new/Sets_Comparable.py
    rm ./specs-new/Console_CloseReader.py
    rm ./specs-new/UnsafeMapIterator.py
    rm ./specs-new/UnsafeListIterator.py
    rm ./specs-new/Pydocs_UselessFileOpen.py

    cd ../$(basename "$link" .git)
fi

########################################################
#                    RUN EXPERIMENT                    #
########################################################
echo "Running experiment..."

results_dir="../results"

if [ ! -d "$results_dir" ]; then
    mkdir "$results_dir"
fi

# save git info
sha=$(git rev-parse HEAD | cut -c1-7)
url=$(git remote get-url origin)
echo "{\"sha-commit\": \"$sha\", \"project-url\": \"$url\"}" > $results_dir/project_info.json


rm -f .pymon

echo ============= Specs being used are =============
if [ -d "$PWD"/../mop-with-dynapt/specs-new/ ]; then
    ls -al "$PWD"/../mop-with-dynapt/specs-new/
fi
echo ================================================ 

set -x
export PYTHONIOENCODING=utf8

START_TIME=$(python3 -c 'import time; print(time.time())')
echo "START_TIME: $START_TIME"
if [ "$algo" = "original" ]; then
    # Run without pythonmop
    timeout $timeout pytest \
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
    timeout $timeout pytest \
        --color=no \
        -v \
        -p pythonmop \
        -rA \
        --path="$PWD"/../mop-with-dynapt/specs-new/ \
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


ls -l $results_dir

########################################################
#                      SAVE RESULTS                    #
########################################################

# Zip file name: repo-name-algo-sha.tar.gz
zip_file="../__results__/$(basename "$link" .git)-$algo-$sha.tar.gz"

# compress results dir
tar -czvf $zip_file $results_dir

# No need to perform cleanup as this will run in a Docker container
# deactivate
# cd ..
# rm -rf $(basename "$link" .git)
# rm -rf venv
# rm -rf mop-with-dynapt
