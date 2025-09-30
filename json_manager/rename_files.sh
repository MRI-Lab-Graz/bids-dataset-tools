#!/bin/bash

# Function to rename files and directories recursively
rename_recursive() {
  local search_string="$1"
  local replace_string="$2"
  local start_directory="$3"

  for file in "$start_directory"/*; do
    if [ -d "$file" ]; then
      # If it's a directory, recursively call the function
      rename_recursive "$search_string" "$replace_string" "$file"
    elif [ -f "$file" ]; then
      # If it's a file, rename it
      local dir_path="$(dirname "$file")"
      local filename="$(basename "$file")"
      local new_filename="${filename//$search_string/$replace_string}"
      if [ "$filename" != "$new_filename" ]; then
        mv "$file" "$dir_path/$new_filename"
        echo "Renamed: $file -> $dir_path/$new_filename"
      fi
    fi
  done
}

# Function to display usage
usage() {
  echo "Usage: $0 -s <search_string> -r <replace_string> -f <start_directory>"
  exit 1
}

# Parse options
while getopts ":s:r:f:" opt; do
  case $opt in
    s) search_string="$OPTARG"
    ;;
    r) replace_string="$OPTARG"
    ;;
    f) start_directory="$OPTARG"
    ;;
    \?) echo "Invalid option -$OPTARG" >&2
        usage
    ;;
    :) echo "Option -$OPTARG requires an argument." >&2
       usage
    ;;
  esac
done

# Check if all required arguments are provided
if [ -z "$search_string" ] || [ -z "$replace_string" ] || [ -z "$start_directory" ]; then
  usage
fi

# Call the rename function with parsed arguments
rename_recursive "$search_string" "$replace_string" "$start_directory"
