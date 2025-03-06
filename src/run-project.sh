#!/bin/sh

echo "Running project..."

# Parse arguments
while [ $# -gt 0 ]; do
  case "$1" in
    --link)
      link="$2"
      shift 2
      ;;
    --sha)
      sha="$2"
      shift 2
      ;;
    --timeout)
      timeout="$2"
      shift 2
      ;;
    --algorithms)
      algos="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Check if all required inputs are provided
if [ -z "$link" ] || [ -z "$sha" ] || [ -z "$algos" ] || [ -z "$timeout" ]; then
  echo "Error: Missing required arguments."
  echo "Usage: $0 --link <link> --sha <sha> --timeout <timeout> --algorithms <algos>"
  exit 1
fi

echo "Inputs received:"
echo "Link: $link"
echo "SHA: $sha"
echo "Timeout: $timeout"
echo "Algorithms: $algos"

########################################################
#                     CLONE REPO                       #
########################################################
echo "Cloning repository..."

retry_count=0
max_retries=10
while [ $retry_count -lt $max_retries ]; do
  git clone --depth 1 "$link" && break
  retry_count=$((retry_count + 1))
  echo "Clone failed. Retrying in 10 seconds... ($retry_count/$max_retries)"
  sleep 10
done

if [ $retry_count -eq $max_retries ]; then
  echo "Error: Failed to clone repository after $max_retries attempts."
  exit 1
fi

cd "$(basename "$link" .git)"

# Checkout the SHA
if [ -n "$sha" ]; then
  echo "Checking out SHA: $sha"
  git fetch origin "$sha" --depth 1
  git checkout "$sha"
else
  echo "SHA is empty, no checkout performed."
fi


# save git info
sha=$(git rev-parse HEAD | cut -c1-7)
########################################################
#                 INSTALL DEPENDENCIES                 #
########################################################
echo "Installing dependencies..."

# Create and activate a virtual environment
python3 -m venv venv
. venv/bin/activate

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
########################################################
#              ALGORITHM-SPECIFIC SETUP                 #
########################################################

# clone and install pymop if algo is not original
echo "Installing pymop from pre-installed dependencies..."

cd /opt/mop-with-dynapt
  pip install wheel
  pip install .
cd -


# Copy pre-installed packages from the permanent venv to the current one
# cp -r /opt/pymop_venv/lib/python3*/site-packages/* venv/lib/python3*/site-packages/

# delete some problematic specs
rm -f /opt/mop-with-dynapt/specs-new/TfFunction_NoSideEffect.py
#rm -f /opt/mop-with-dynapt/specs-new/CreateWidgetOnSameFrameCanvas.py
#rm -f /opt/mop-with-dynapt/specs-new/Turtle_LastStatementDone.py
#rm -f /opt/mop-with-dynapt/specs-new/Pydocs_MustShutdownProcessPoolExecutor.py  
#rm -f /opt/mop-with-dynapt/specs-new/Pydocs_MustShutdownExecutor.py
#rm -f /opt/mop-with-dynapt/specs-new/Pydocs_UselessProcessPoolExecutor.py 
#rm -f /opt/mop-with-dynapt/specs-new/Pydocs_UselessThreadPoolExecutor.py
#rm -f /opt/mop-with-dynapt/specs-new/Pydocs_MustShutdownThreadPoolExecutor.py
#rm -f /opt/mop-with-dynapt/specs-new/faulthandler_disableBeforeClose.py  
#rm -f /opt/mop-with-dynapt/specs-new/faulthandler_tracetrackDumpBeforeClose.py
#rm -f /opt/mop-with-dynapt/specs-new/faulthandler_unregisterBeforeClose.py
#rm -f /opt/mop-with-dynapt/specs-new/UnsafeArrayIterator.py

# new
#rm -f /opt/mop-with-dynapt/specs-new/PyDocs_MustLockOnce.py
rm -f /opt/mop-with-dynapt/specs-new/PyDocs_SharedMemoryUseAfterUnlink.py
#rm -f /opt/mop-with-dynapt/specs-new/Pydocs_HTTPConnectionSendSequence.py


#sanity check owolabi
# Diretórios de origem e destino
SRC_DIR="/opt/mop-with-dynapt/specs-new"
DEST_DIR="/tmp/specs_old"

# Criar o diretório de destino se não existir
mkdir -p "$DEST_DIR"

# Lista de arquivos que devem ser movidos
#FILES_TO_MOVE="
#PyDocs_MustSortBeforeGroupBy.py
#PyDocs_UnsafeIterUseAfterTee.py
#PyDocs_UselessIterTee.py
#UnsafeArrayIterator.py"

# Mover os arquivos para o diretório de destino
#for file in $FILES_TO_MOVE; do
#    if [ -e "$SRC_DIR/$file" ]; then
#        mv "$SRC_DIR/$file" "$DEST_DIR"/
#    fi
#done


pip3 install pytest-json-report memray pytest-memray pytest-cov pytest-env pytest-rerunfailures pytest-socket pytest-django austin-dist

owner=$(basename $(dirname "$link"))
repo=$(basename "$link" .git)

installed=false
# Loop through all algorithms
# algos="B"
for algo in $algos; do
    echo "Running algorithm: $algo"
    
    
    ########################################################
    #                    RUN EXPERIMENT                    #
    ########################################################
    echo "Running experiment for $algo..."

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

    echo "============= Specs being used are ============="
    if [ -d /opt/mop-with-dynapt/specs-new ]; then
        ls -al /opt/mop-with-dynapt/specs-new
    fi
    echo "================================================"

    set -x
    export PYTHONIOENCODING=utf8

    START_TIME=$(python3 -c 'import time; print(time.time())')
    echo "START_TIME: $START_TIME"
    
    if [ "$algo" = "ORIGINAL" ]; then
        # Run without pythonmop
        timeout $timeout pytest \
            -p no:pythonmop \
            --color=no \
            -v \
            -rA \
            --continue-on-collection-errors > $results_dir/$algo-pytest-output.txt 2>&1
    else
        timeout $timeout pytest \
            --color=no \
            -v \
            -p pythonmop \
            -rA \
            --path=/opt/mop-with-dynapt/specs-new/\
            --algo $algo \
            --continue-on-collection-errors \
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

    # Move result files if they exist
    [ -f .report.json ] && mv .report.json $results_dir/$algo.report.json
    [ -f "$algo"-full.json ] && mv "$algo"-full.json $results_dir/$algo-full.json
    [ -f "$algo"-violations.json ] && mv "$algo"-violations.json $results_dir/$algo-violations.json
    [ -f "$algo"-time.json ] && mv "$algo"-time.json $results_dir/$algo-time.json
    [ -f $algo-profile.austin ] && mv $algo-profile.austin $results_dir/$algo-profile.austin
    [ -f $algo-profile-flamegraph.svg ] && mv $algo-profile-flamegraph.svg $results_dir/$algo-profile-flamegraph.svg

    ls -l $results_dir

    ########################################################
    #                      SAVE RESULTS                    #
    ########################################################

    # Zip file name: owner-repo-algo-sha.zip
    zip_file="../__results__/$full_project_name.tar.gz"

    # compress results dir
    chmod 777 $results_dir
    tar -czvf $zip_file $results_dir
    chmod 777 $zip_file

    echo "!!!done $algo!!!"
done

echo "All algorithms completed!"