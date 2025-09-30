# Tools for EventFiles
## BIDS Events Converter (pres2bids.py)

This script converts log files from Neurobehavioral Systems' Presentation software to BIDS-compatible events files. It also generates a summary log file with key information from the log files.

### Features

- Converts Presentation log files to BIDS events files.
- Extracts and adjusts event times relative to the first "Pulse" event.
- Groups events by specified search strings found within the `Code` column.
- Generates a summary log file with scenario name, log file creation time, subject ID, and event counts.

### Prerequisites

- Python 3.x

### Usage

#### Command Line Arguments

- `LOG_DIR_PATH`: Path to the directory containing Presentation log files.
- `EVENTS_OUTPUT_DIR`: Path to the directory to save output BIDS events files.
- `SUMMARY_OUTPUT_PATH`: Path to save the summary log file.
- `--start-event-code`: (Optional) Event code that marks the task start after syncing with the scanner. Default is `Beginn`.
- `--search-strings`: (Optional) Comma-separated list of strings to search for within the `Code` column. Default is `Fixation,Rest,Response`.

#### Example Command

```sh
python pres2bids.py log_files/ bids/ summary_log.tsv --start-event-code Beginn --search-strings Fixation,Response,Mask,Comp,Hit
```
## BIDS Events File Organizer (copy2bids.sh)

This Bash script organizes and copies event log files into a BIDS-compliant directory structure. It reads event files from a specified source directory and places them into the appropriate subdirectories within a BIDS folder based on the filenames. If the required BIDS folder structure does not exist, the script will create it and issue a warning.

### Features

- Parses event filenames to determine target directories
- Verifies and creates necessary directories within the BIDS structure
- Issues warnings for event files with fewer than 5 lines
- Displays a custom header with the current date and time at the start of the script

### Usage

```bash
./copy2bids.sh -e /path/to/events -b /path/to/BIDS
```
