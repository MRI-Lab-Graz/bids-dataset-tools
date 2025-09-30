#!/bin/bash

# BIDS Rename Manager - shell wrapper for entity-aware filename renaming

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/bids_rename_manager.py"

print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

check_dependencies() {
    if ! command -v python3 >/dev/null 2>&1; then
        print_color $RED "Error: python3 is required but not installed"
        exit 1
    fi

    if [ ! -f "$PYTHON_SCRIPT" ]; then
        print_color $RED "Error: Python script not found at $PYTHON_SCRIPT"
        exit 1
    fi
}

show_usage() {
    cat <<EOF
$(print_color $BLUE "BIDS Rename Manager - Safely rename BIDS files")

USAGE:
    $0 [options]

KEY OPTIONS:
    -r, --root DIR          Root of the BIDS dataset (required)
    -p, --pattern GLOB      Optional glob to limit files (default: *)
    --ses SESSION           Restrict to a session (e.g. --ses 2 or --ses 02)
    --modality MODALITY     Restrict to modality folder (anat, func, dwi, ...)
    --file PATTERN          fnmatch pattern applied to filenames
    --remove-substring STR  Remove literal substrings (can specify multiple)
    --replace OLD:NEW       Replace substring pairs (multiple allowed)
    --set-entity key=value  Set or add entity values (multiple allowed)
    --remove-entity key     Remove entities (e.g., acq)
    --dry-run               Preview operations without touching files
    --no-backup             Skip copying originals to sourcedata/backup
    --verbose               Detailed logging

EXAMPLES:
    # Remove acquisition label from functional runs
    $0 -r /data/bids --modality func --remove-entity acq

    # Insert new description entity on anatomical files
    $0 -r /data/bids --modality anat --set-entity desc=T1wClean

    # Replace substring and keep run entity
    $0 -r /data/bids --replace "old:rest" --set-entity run=01

    # Dry-run with session filter
    $0 -r /data/bids --ses 2 --modality func --remove-substring "_pilot" --dry-run
EOF
}

main() {
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi

    check_dependencies

    if [[ "$1" == "help" || "$1" == "--help" || "$1" == "-h" ]]; then
        show_usage
        exit 0
    fi

    python3 "$PYTHON_SCRIPT" "$@"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
