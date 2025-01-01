#!/bin/bash

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd $HERE/../results

# for f in *.zip; do
#   folder_name=$(echo "${f%.*}" | sed -E 's/(-ORIGINAL|-A|-B|-C\+?|-D)$//')
#   unzip -o -d "$folder_name" "$f"
#   rm "$f"
# done


for f in *.tar.gz; do
    folder_name=$(echo "${f%.*.*}" | sed -E 's/(-ORIGINAL|-A|-B|-C\+?|-D)$//')
    mkdir -p "$folder_name"
    temp_dir=$(mktemp -d)
    tar -xzf "$f" -C "$temp_dir"
    mv "$temp_dir"/*/* "$folder_name"
    rm -r "$temp_dir"
    rm "$f"
done