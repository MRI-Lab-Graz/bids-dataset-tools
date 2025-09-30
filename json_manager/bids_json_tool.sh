#!/bin/bash

# BIDS JSON Manager - Shell wrapper for easy JSON tag management
# This is an improved version of the original rename_json.sh with enhanced functionality

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/bids_json_manager.py"

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check dependencies
check_dependencies() {
    if ! command -v python3 &> /dev/null; then
        print_color $RED "Error: python3 is required but not installed"
        exit 1
    fi
    
    if [ ! -f "$PYTHON_SCRIPT" ]; then
        print_color $RED "Error: Python script not found at $PYTHON_SCRIPT"
        exit 1
    fi
}

# Function to display usage
show_usage() {
    cat << EOF
$(print_color $BLUE "BIDS JSON Manager - Easy JSON tag management for BIDS datasets")

USAGE:
    $0 <command> [options]

COMMANDS:
    add             Add a new JSON tag to files
    remove          Remove a JSON tag from files  
    modify          Modify existing tag values
    replace         Replace strings in tag values (legacy)
    list            List all tags found in dataset
    validate        Validate JSON file structure
    copy-tags       Copy tags from source to target files
    diff            Compare tags between two sets of files
    template        Apply BIDS template configurations
    list-templates  List available BIDS templates
    check-compliance Check BIDS compliance of JSON files
    map-tags        Rename/map tags systematically
    stats           Show dataset statistics
    help            Show this help message

COMMON OPTIONS:
    -r, --root DIR       Root directory of BIDS dataset (required)
    -p, --pattern GLOB   File pattern to match (default: *.json)
    -v, --verbose        Enable verbose output
    --no-backup         Skip creating backup files
    --dry-run, -n       Preview operations without making changes

BIDS FILTERING OPTIONS:
    --ses, --session N   Target specific session (e.g., --ses 1 or --ses 01)
    --anat              Target anatomical data only
    --func              Target functional data only  
    --fmap              Target field map data only
    --dwi               Target diffusion data only
    --perf              Target perfusion data only
    --meg               Target MEG data only
    --eeg               Target EEG data only
    --ieeg              Target iEEG data only
    --beh               Target behavioral data only
    --file PATTERN      Target files matching filename pattern

EXAMPLES:
    # Basic operations
    $0 add -r /path/to/bids --tag TaskName --value '"rest"'
    $0 remove -r /path/to/bids --tag SliceTiming
    
    # BIDS-aware filtering
    $0 add -r /path/to/bids --tag TaskName --value '"faces"' --func
    $0 remove -r /path/to/bids --tag EchoTime --anat
    $0 modify -r /path/to/bids --tag PhaseEncodingDirection --value '"j-"' --fmap
    
    # Session-specific operations
    $0 add -r /path/to/bids --tag Instructions --value '"Keep eyes closed"' --ses 1
    $0 list -r /path/to/bids --ses 01 --func
    
    # Filename pattern targeting
    $0 add -r /path/to/bids --tag TaskName --value '"rest"' --file "*rest*"
    $0 remove -r /path/to/bids --tag SliceTiming --file "*bold*"
    
    # Combined filtering
    $0 modify -r /path/to/bids --tag RepetitionTime --value 2.5 --ses 2 --func --file "*task-rest*"
    
    # Advanced operations
    $0 copy-tags -r /path/to/bids --from-pattern "*func*rest*" --to-pattern "*func*faces*" --tags TaskName Instructions
    $0 diff -r /path/to/bids --pattern1 "*func*.json" --pattern2 "*anat*.json"
    $0 template -r /path/to/bids --name func-rest --func --dry-run
    $0 list-templates
    
    # New advanced features
    $0 check-compliance -r /path/to/bids --func
    $0 map-tags -r /path/to/bids --mapping "TR:RepetitionTime,TE:EchoTime" --delete-source
    $0 stats -r /path/to/bids --detailed
    
    # Replace string in SeriesDescription (legacy mode)
    $0 replace -r /path/to/bids --tag SeriesDescription --search "old" --replace "new"
    
    # List all tags in functional data only
    $0 list -r /path/to/bids --func
    
    # Validate all JSON files
    $0 validate -r /path/to/bids

For detailed help on specific commands, use:
    $0 <command> --help

EOF
}

# Function to show command-specific help
show_command_help() {
    local command=$1
    python3 "$PYTHON_SCRIPT" "$command" --help
}

# Main script logic
main() {
    # Check if no arguments provided
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi
    
    # Check dependencies
    check_dependencies
    
    # Handle help commands
    local command=$1
    case "$command" in
        help|--help|-h)
            show_usage
            exit 0
            ;;
        add|remove|modify|replace|list|validate|copy-tags|diff|template|list-templates|check-compliance|map-tags|stats)
            # Check if user wants help for specific command
            if [[ "$2" == "--help" || "$2" == "-h" ]]; then
                show_command_help "$command"
                exit 0
            fi
            # Pass all arguments to Python script
            python3 "$PYTHON_SCRIPT" "$@"
            ;;
        *)
            print_color $RED "Error: Unknown command '$command'"
            print_color $YELLOW "Use '$0 help' to see available commands"
            exit 1
            ;;
    esac
}

# Quick command functions for convenience
bids_add() {
    python3 "$PYTHON_SCRIPT" add "$@"
}

bids_remove() {
    python3 "$PYTHON_SCRIPT" remove "$@"
}

bids_modify() {
    python3 "$PYTHON_SCRIPT" modify "$@"
}

bids_list() {
    python3 "$PYTHON_SCRIPT" list "$@"
}

bids_validate() {
    python3 "$PYTHON_SCRIPT" validate "$@"
}

# Export functions if script is sourced
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    export -f bids_add bids_remove bids_modify bids_list bids_validate
else
    # Script is executed directly
    main "$@"
fi