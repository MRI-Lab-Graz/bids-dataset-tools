#!/bin/bash

# Function to print header with terminal artwork
print_header() {
    echo -e "\033[1;32m"  # Set color to green
    echo "==================================================="
    echo "                     MRI - LAB GRAZ"
    echo "==================================================="
    echo -e "\033[0m"  # Reset to default color
    echo "Date: $(date '+%Y-%m-%d')"
    echo "Time: $(date +%H:%M)"
    echo "---------------------------------------------------"
}

# Initialize variables for source_dir, bids_root_dir, and file_type
source_dir=""
bids_root_dir=""
file_type=""

# Print the header
print_header

# Process command-line options using while loop and case statement
while [[ $# -gt 0 ]]; do
    key="$1"

    case $key in
        -e|--events)
            source_dir="$2"
            shift # past argument
            shift # past value
            ;;
        -b|--bids)
            bids_root_dir="$2"
            shift # past argument
            shift # past value
            ;;
        -t|--type)
            file_type="$2"
            shift # past argument
            shift # past value
            ;;
        *)    # unknown option
            echo "Usage: $0 -e /path/to/source -b /path/to/BIDS -t events|physio"
            exit 1
            ;;
    esac
done

# Check if the source and BIDS root directories and file_type are set
if [ -z "$source_dir" ] || [ -z "$bids_root_dir" ] || [ -z "$file_type" ]; then
    echo "Error: Source directory, BIDS root directory, and file type must be specified."
    echo "Usage: $0 -e /path/to/source -b /path/to/BIDS -t events|physio"
    exit 1
fi

# Check if file_type is valid
if [ "$file_type" != "events" ] && [ "$file_type" != "physio" ]; then
    echo "Error: File type must be either 'events' or 'physio'."
    exit 1
fi

# Check if the source and BIDS root directories exist
if [ ! -d "$source_dir" ] || [ ! -d "$bids_root_dir" ]; then
    echo "Error: Check that both the source directory ($source_dir) and the BIDS root directory ($bids_root_dir) exist."
    exit 1
fi

# Process files based on file_type
if [ "$file_type" == "events" ]; then
    # Loop over each event file in the source directory
    for file in "$source_dir"/*_events.tsv; do
        # Check if file exists (in case no files match the pattern)
        if [ ! -f "$file" ]; then
            echo "No events files found in $source_dir"
            exit 1
        fi

        # Extract the base filename without the path
        base_filename=$(basename "$file")

        # Check if the events file has 5 lines or fewer
        line_count=$(wc -l < "$file")
        if [ "$line_count" -le 5 ]; then
            echo "Warning: Events file seems to be too small, please check your data - $file"
            continue  # Skip to the next file or add additional handling as needed
        fi

        # Parse necessary components from the filename
        sub=$(echo "$base_filename" | grep -o 'sub-[^_]*')
        ses=$(echo "$base_filename" | grep -o 'ses-[^_]*')

        # Construct the target directory path
        target_dir="$bids_root_dir/$sub/$ses/func"

        # Check if the expected BIDS structure exists
        if [ ! -d "$target_dir" ]; then
            echo "Warning: Target directory structure ($target_dir) does not exist. File will still be copied, but please verify structure."
            mkdir -p "$target_dir"
        fi

        # Copy the file to the target directory
        cp "$file" "$target_dir/"
    done

elif [ "$file_type" == "physio" ]; then
    # Loop over each physio file (tsv.gz) in the source directory
    for file in "$source_dir"/*_physio.tsv.gz; do
        # Check if file exists (in case no files match the pattern)
        if [ ! -f "$file" ]; then
            echo "No physio files found in $source_dir"
            exit 1
        fi

        # Extract the base filename without the extension
        base_filename=$(basename "$file" .tsv.gz)

        # Parse necessary components from the filename
        sub=$(echo "$base_filename" | grep -o 'sub-[^_]*')
        ses=$(echo "$base_filename" | grep -o 'ses-[^_]*')

        # Construct the target directory path
        target_dir="$bids_root_dir/$sub/$ses/func"

        # Check if the expected BIDS structure exists
        if [ ! -d "$target_dir" ]; then
            echo "Warning: Target directory structure ($target_dir) does not exist. Files will still be copied, but please verify structure."
            mkdir -p "$target_dir"
        fi

        # Copy both the tsv.gz and json files to the target directory
        tsv_gz_file="$file"
        json_file="$source_dir/$base_filename.json"

        # Check if JSON file exists
        if [ ! -f "$json_file" ]; then
            echo "Warning: Corresponding JSON file not found for $tsv_gz_file"
        else
            cp "$json_file" "$target_dir/"
        fi

        cp "$tsv_gz_file" "$target_dir/"
    done
fi

echo "All files have been copied successfully."
