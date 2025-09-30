#!/bin/bash

# BIDS Event Importer - shell wrapper for copying events/physio files into BIDS datasets

set -e

RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/bids_event_importer.py"

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
$(print_color $BLUE "BIDS Event Importer - Copy events/physio files into BIDS datasets")

USAGE:
    $0 -s /path/to/source -b /path/to/bids [options]

KEY OPTIONS:
    -s, --source DIR       Directory with new *_events.tsv or *_physio.tsv.gz files (required)
    -b, --bids-root DIR    Root of the target BIDS dataset (required)
    --physio               Include physio files (default: only events)
    --events               Explicitly include events files (enabled by default)
    --pattern GLOB         Additional fnmatch filter for filenames
    --ses SESSION          Restrict to a specific session (e.g. 2 or 02)
    --sub SUBJECT          Restrict to a specific subject (e.g. sub-01)
    --overwrite            Replace conflicting files at the destination
    --dry-run              Preview operations without copying
    --verbose              Detailed logging

EXAMPLES:
    # Dry-run import of events files after preprocessing
    $0 -s /incoming/events -b /data/bids --dry-run

    # Copy physio pairs as well, overwriting existing sidecars
    $0 -s /incoming/physio -b /data/bids --events --physio --overwrite

    # Limit to a single session and subject
    $0 -s /incoming/events -b /data/bids --ses 2 --sub sub-07
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
