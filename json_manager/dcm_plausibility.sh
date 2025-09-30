#!/bin/bash

# Function to extract DICOM tags
extract_dicom_info() {
  local dcm_file=$1
  local date_tag=$(dcminfo "$dcm_file" -tag 0008 0022 | awk '{print $2}')
  local time_tag=$(dcminfo "$dcm_file" -tag 0008 0032 | awk '{print $2}')
  echo "$date_tag $time_tag"
}

# Function to format the date based on the OS
format_date() {
  local dicom_date=$1
  if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    gdate -d "$dicom_date" +"%d-%m-%Y"
  else
    # Linux
    date -d "$dicom_date" +"%d-%m-%Y"
  fi
}

# Function to check if the times are within 90 minutes
check_time_difference() {
  local start_time=$1
  local end_time=$2
  if [[ "$OSTYPE" == "darwin"* ]]; then
    local start_seconds=$(gdate -d "$start_time" +%s)
    local end_seconds=$(gdate -d "$end_time" +%s)
  else
    local start_seconds=$(date -d "$start_time" +%s)
    local end_seconds=$(date -d "$end_time" +%s)
  fi
  local time_diff=$(( (end_seconds - start_seconds) / 60 ))
  if (( time_diff > 90 )); then
    echo "false"
  else
    echo "true"
  fi
}

# Root directory containing DICOM files
root_dir="$1"

echo "Scanning DICOM files in directory: $root_dir"

# Iterate over all subject directories
for subject_dir in "$root_dir"/sub-*; do
  subject=$(basename "$subject_dir")
  
  # Iterate over all session directories
  for session_dir in "$subject_dir"/ses-*; do
    session=$(basename "$session_dir")

    declare -a dates
    declare -a times

    # Iterate over all subfolders in the session directory
    for subfolder in "$session_dir"/*; do
      # Find the first DICOM file in the subfolder
      first_dcm_file=$(find "$subfolder" -type f -name "*.dcm" | head -n 1)
      
      if [[ -n "$first_dcm_file" ]]; then
        dicom_info=$(extract_dicom_info "$first_dcm_file")
        dicom_date=$(echo "$dicom_info" | awk '{print $1}')
        dicom_time=$(echo "$dicom_info" | awk '{print $2}')

        # Store dates and times for later checks
        dates+=("$dicom_date")
        times+=("$dicom_date $dicom_time")

        # Format the date
        formatted_date=$(format_date "$dicom_date")

        subfolder_name=$(basename "$subfolder")

        echo "Subject $subject in Session $session, Folder $subfolder_name was acquired on $formatted_date at $dicom_time"
      else
        echo "No DICOM files found in $subfolder"
      fi
    done

    # Check if all dates are the same
    unique_dates=($(echo "${dates[@]}" | tr ' ' '\n' | sort -u | tr '\n' ' '))
    if (( ${#unique_dates[@]} != 1 )); then
      echo -e "\033[31mWarning: DICOM files in $subject/$session were not acquired on the same date.\033[0m"
    else
      # Sort times and check the maximal time difference
      IFS=$'\n' sorted_times=($(sort <<<"${times[*]}"))
      unset IFS
      start_time="${sorted_times[0]}"
      end_time="${sorted_times[${#sorted_times[@]}-1]}"

      if [[ $(check_time_difference "$start_time" "$end_time") == "false" ]]; then
        echo -e "\033[31mWarning: DICOM files in $subject/$session were not acquired within a 90-minute range.\033[0m"
      fi
    fi

    # Clear arrays for the next session
    dates=()
    times=()
  done
done

exit 0
