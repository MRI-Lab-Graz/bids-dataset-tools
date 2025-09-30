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
## BIDS Events & Physio Importer (`bids_event_importer.py` + `bids_event_tool.sh`)

Modern replacement for `copy2bids.sh`. This tool mirrors the experience of the JSON/rename managers and safely copies new `_events.tsv` and `_physio.tsv[.gz]` files into an existing BIDS dataset using BIDS-aware pattern matching.

### Highlights

- ✅ Supports both events (`*_events.tsv`) and physio (`*_physio.tsv.gz`) sidecars
- ✅ Automatically detects the correct subject/session folder and searches for matching modality directories
- ✅ Falls back to sensible defaults (`func`, `beh`) when the exact data file is not yet present
- ✅ Dry-run and verbose modes for transparent previews
- ✅ Optional overwriting of existing files, with per-file skip summaries
- ✅ Copies accompanying physio JSON sidecars when available
- ✅ Minimum line-count safeguard for suspiciously small events files

### Quick Start

```bash
# Preview where files would land
./bids_event_tool.sh -s /incoming/events -b /data/bids --dry-run

# Copy both events and physio sidecars, overwriting existing files if necessary
./bids_event_tool.sh -s /incoming -b /data/bids --events --physio --overwrite

# Restrict to a particular session/subject and use verbose logging
./bids_event_tool.sh -s /incoming -b /data/bids --ses 2 --sub sub-05 --verbose
```

### Python Entry Point

```bash
python EventFile/bids_event_importer.py --source /incoming --bids-root /data/bids --physio --dry-run
```

### Legacy Script (for reference)

- `copy2bids.sh`: Original Bash implementation (still available but superseded by the new importer)
