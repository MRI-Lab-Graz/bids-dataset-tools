#!/bin/bash

# --- Default values ---
dry_run=false
find_digits_after=""

# --- Parse arguments ---
while [[ "$#" -gt 0 ]]; do
  case $1 in
    -b) root_dir="$2"; shift ;;
    -l) log_dir="$2"; shift ;;
    -fd) find_digits_after="$2"; shift ;;
    --dry-run) dry_run=true ;;
    -h|--help)
      echo "Usage: $0 -b /path/to/BIDS_root -l /path/to/log_files [-fd pattern] [--dry-run]"
      echo "       -fd: find 3-digit code right before this string in the filename"
      exit 0
      ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
  shift
done

# --- Validate ---
if [[ -z "$root_dir" || -z "$log_dir" ]]; then
  echo "Missing required arguments."
  echo "Usage: $0 -b /path/to/BIDS_root -l /path/to/log_files [-fd pattern] [--dry-run]"
  exit 1
fi

# Normalize paths (remove trailing slash)
root_dir="${root_dir%/}"
log_dir="${log_dir%/}"
sourcedata_dir="$root_dir/sourcedata"
rawdata_dir="$root_dir/rawdata"

if [ ! -d "$rawdata_dir" ]; then
  echo "❌ Raw BIDS directory not found at $rawdata_dir"
  exit 1
fi

if [ ! -d "$log_dir" ]; then
  echo "❌ Log directory not found at $log_dir"
  exit 1
fi

echo "📁 BIDS root: $root_dir"
echo "📁 Rawdata:   $rawdata_dir"
echo "📁 Logs from: $log_dir"
echo "🔎 Pattern to find digits: ${find_digits_after:-default (.log ending)}"
echo "🚦 Dry-run mode: $dry_run"
echo

# --- Inside the loop over log files ---
for log_file in "$log_dir"/*.log; do
  filename=$(basename "$log_file")

  # Extract 3-digit code (via -fd if set, or default)
  if [[ -n "$find_digits_after" ]]; then
    code=$(echo "$filename" | grep -oP "[0-9]{3}(?=${find_digits_after})")
  else
    [[ "$filename" =~ ([0-9]{3})\.log$ ]] && code="${BASH_REMATCH[1]}"
  fi

  if [[ -n "$code" ]]; then
    # New matching logic: find BIDS file with 3-digit code embedded in sub-XXX
    bids_bold_file=$(find "$rawdata_dir" -type f -name "sub-*${code}*_ses-*_bold.nii.gz" | head -n 1)

    if [ -n "$bids_bold_file" ]; then
      bold_filename=$(basename "$bids_bold_file")
      sub=$(echo "$bold_filename" | grep -oP 'sub-[^_]+')
      ses=$(echo "$bold_filename" | grep -oP 'ses-[^_]+')

      new_name="${bold_filename/.nii.gz/_events.txt}"
      dest_dir="$sourcedata_dir/$sub/$ses/func"

      if $dry_run; then
        echo "[Dry Run] Would create: $dest_dir"
        echo "[Dry Run] Would copy $filename → $dest_dir/$new_name"
      else
        mkdir -p "$dest_dir"
        echo "✅ Copying $filename → $dest_dir/$new_name"
        cp "$log_file" "$dest_dir/$new_name"
      fi
    else
    echo "⚠️  No BIDS bold file found with subject code *${code}* ($filename)"
  
    mismatch_dir="$sourcedata_dir/mismatch"
    mkdir -p "$mismatch_dir"

  if $dry_run; then
    echo "[Dry Run] Would copy $filename → $mismatch_dir/$filename"
  else
    echo "🚧 Moving $filename to mismatch folder for manual review"
    cp "$log_file" "$mismatch_dir/$filename"
  fi

    fi
  else
    echo "⚠️  Could not extract 3-digit code from $filename"
  fi
done
