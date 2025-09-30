#!/bin/bash

# Function to replace a string in a specific JSON tag recursively
replace_string_in_json_tag() {
  local search_string="$1"
  local replace_string="$2"
  local json_tag="$3"
  local start_directory="$4"

  find "$start_directory" -type f -name "*.json" | while read -r file; do
    if grep -q "\"$json_tag\"" "$file"; then
      jq --arg search "$search_string" --arg replace "$replace_string" --arg tag "$json_tag" '
        (.. | objects | select(has($tag)) | .[$tag] | arrays | .[]) |= gsub($search; $replace)
      ' "$file" > "$file.tmp" && mv "$file.tmp" "$file"
      echo "Updated: $file"
    fi
  done
}

# Function to print the usage of the script
print_usage() {
  echo "Usage: $0 -s <search_string> -r <replace_string> -j <json_tag> -f <start_directory>"
  exit 1
}

# Parse arguments
while getopts 's:r:j:f:' flag; do
  case "${flag}" in
    s) search_string="${OPTARG}" ;;
    r) replace_string="${OPTARG}" ;;
    j) json_tag="${OPTARG}" ;;
    f) start_directory="${OPTARG}" ;;
    *) print_usage ;;
  esac
done

# Check if all required arguments are provided
if [ -z "$search_string" ] || [ -z "$replace_string" ] || [ -z "$json_tag" ] || [ -z "$start_directory" ]; then
  print_usage
fi

replace_string_in_json_tag "$search_string" "$replace_string" "$json_tag" "$start_directory"
