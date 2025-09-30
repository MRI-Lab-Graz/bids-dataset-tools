# BIDS Helper Tools

This directory contains tools to help manage and modify BIDS (Brain Imaging Data Structure) datasets, with a focus on JSON sidecar file management.

## 🚀 Quick Start

The main tool for JSON management is `bids_json_tool.sh` (shell wrapper) or `bids_json_manager.py` (Python script directly).

### Basic Usage

```bash
# Add a new tag to all JSON files
./bids_json_tool.sh add -r /path/to/bids --tag TaskName --value '"rest"'

# Remove a tag from all files  
./bids_json_tool.sh remove -r /path/to/bids --tag SliceTiming

# List all tags in your dataset
./bids_json_tool.sh list -r /path/to/bids

# Rename filenames safely (dry-run first!)
./bids_rename_tool.sh -r /path/to/bids --modality func --remove-entity acq --dry-run
```

## 📋 Available Tools

### 1. BIDS JSON Manager (`bids_json_manager.py` + `bids_json_tool.sh`)

**Purpose**: Comprehensive tool for managing JSON sidecar files in BIDS datasets

**Key Features**:
- ✅ Add new JSON tags/fields
- ✅ Remove existing JSON tags
- ✅ Modify tag values
- ✅ Replace strings within tag values (legacy support)
- ✅ List all tags in dataset
- ✅ Validate JSON file structure
- ✅ **BIDS-aware filtering**: Target specific sessions, modalities, and filename patterns
- ✅ **Session filtering**: --ses 1, --ses 01
- ✅ **Modality filtering**: --anat, --func, --fmap, --dwi, --perf, --meg, --eeg, --ieeg, --beh
- ✅ **Filename filtering**: --file "*rest*", --file "*bold*"
- ✅ **Combined filtering**: Mix session, modality, and filename filters
- ✅ Automatic backup creation
- ✅ Robust error handling
- ✅ Verbose logging options

### 2. BIDS Rename Manager (`bids_rename_manager.py` + `bids_rename_tool.sh`)

**Purpose**: Safely rename BIDS files while respecting entity rules and paired sidecars

**Key Features**:
- ✅ Entity-aware transformations (`--set-entity`, `--remove-entity`)
- ✅ String level edits (`--remove-substring`, `--replace`)
- ✅ Same filtering logic as JSON manager (sessions, modalities, filename patterns)
- ✅ Dry-run previews and verbose logging
- ✅ Optional backups stored under `sourcedata/backup`
- ✅ Handles groups of sidecar/data files together to keep BIDS-valid pairs

### 3. Legacy Tools (for reference)

- `rename_json.sh`: Original string replacement tool (limited functionality)
- `rename_files.sh`: Early file renaming utility (superseded by `bids_rename_manager.py`)
- `dcm_plausibility.sh`: DICOM temporal validation tool

## 📖 Detailed Usage Guide

### Installation & Requirements

**Requirements**:
- Python 3.6+ 
- Standard Python libraries (json, argparse, pathlib)
- Bash shell (for wrapper script)

**Setup**:
```bash
# Make scripts executable (if not already)
chmod +x bids_json_tool.sh
chmod +x bids_json_manager.py
```

### Command Reference

#### Add Tags
```bash
# Add simple string value
./bids_json_tool.sh add -r /path/to/bids --tag TaskName --value '"faces"'

# Add numeric value
./bids_json_tool.sh add -r /path/to/bids --tag RepetitionTime --value 2.0

# Add boolean value
./bids_json_tool.sh add -r /path/to/bids --tag IsCompleted --value true

# Add array value
./bids_json_tool.sh add -r /path/to/bids --tag SliceTiming --value '[0.0, 0.5, 1.0, 1.5]'

# Add to specific file types only
./bids_json_tool.sh add -r /path/to/bids --tag TaskName --value '"rest"' -p "*func*.json"

# Overwrite existing tags
./bids_json_tool.sh add -r /path/to/bids --tag TaskName --value '"new_task"' --overwrite
```

#### Remove Tags
```bash
# Remove tag from all JSON files
./bids_json_tool.sh remove -r /path/to/bids --tag SliceTiming

# Remove from specific file pattern
./bids_json_tool.sh remove -r /path/to/bids --tag EchoTime -p "*fmap*.json"
```

#### Modify Tags
```bash
# Modify existing tag value
./bids_json_tool.sh modify -r /path/to/bids --tag RepetitionTime --value 2.5

# Create tag if it doesn't exist
./bids_json_tool.sh modify -r /path/to/bids --tag NewField --value '"new_value"' --create
```

#### Replace Strings (Legacy Mode)
```bash
# Replace string within tag values
./bids_json_tool.sh replace -r /path/to/bids --tag SeriesDescription --search "old_name" --replace "new_name"

# Works with arrays too
./bids_json_tool.sh replace -r /path/to/bids --tag TaskInstructions --search "press button" --replace "press key"
```

#### List & Validate
```bash
# List all tags in dataset
./bids_json_tool.sh list -r /path/to/bids

# List tags in specific files
./bids_json_tool.sh list -r /path/to/bids -p "*func*.json"

# Validate JSON structure
./bids_json_tool.sh validate -r /path/to/bids
```

### Advanced Options

#### File Patterns
Use glob patterns to target specific files:
- `"*.json"` - All JSON files (default)
- `"*func*.json"` - Functional data JSON files
- `"*anat*.json"` - Anatomical data JSON files  
- `"*fmap*.json"` - Field map JSON files
- `"*dwi*.json"` - Diffusion data JSON files
- `"sub-01/ses-*/func/*.json"` - Specific subject/session

#### Backup Management
```bash
# Skip backup creation (faster but less safe)
./bids_json_tool.sh add -r /path/to/bids --tag NewTag --value '"value"' --no-backup

# Backups are stored under sourcedata/backup with mirrored paths (e.g. func/sub-01_task-bold.json.bak)
```

#### Verbose Output
```bash
# Enable detailed logging
./bids_json_tool.sh add -r /path/to/bids --tag TaskName --value '"rest"' --verbose
```

## 🎯 Common BIDS Use Cases

### 1. Adding Task Information
```bash
# Add task name to functional data
./bids_json_tool.sh add -r /path/to/bids --tag TaskName --value '"rest"' -p "*func*.json"

# Add task instructions
./bids_json_tool.sh add -r /path/to/bids --tag Instructions --value '"Keep eyes closed"' -p "*func*.json"
```

### 2. Fixing Acquisition Parameters
```bash
# Correct RepetitionTime
./bids_json_tool.sh modify -r /path/to/bids --tag RepetitionTime --value 2.0

# Add missing EchoTime
./bids_json_tool.sh add -r /path/to/bids --tag EchoTime --value 0.03 -p "*func*.json"
```

### 3. Managing Slice Timing
```bash
# Remove incorrect slice timing
./bids_json_tool.sh remove -r /path/to/bids --tag SliceTiming

# Add correct slice timing
./bids_json_tool.sh add -r /path/to/bids --tag SliceTiming --value '[0.0, 0.5, 1.0, 1.5, 2.0]'
```

### 4. Dataset Cleanup
```bash
# Remove acquisition software artifacts
./bids_json_tool.sh remove -r /path/to/bids --tag ProtocolName

# Standardize series descriptions
./bids_json_tool.sh replace -r /path/to/bids --tag SeriesDescription --search "BOLD_" --replace "bold_"
```

### 5. Quality Control
```bash
# List all tags to check consistency
./bids_json_tool.sh list -r /path/to/bids

# Validate JSON structure
./bids_json_tool.sh validate -r /path/to/bids
```

## ✂️ Filename Renaming

Use `bids_rename_tool.sh` (or call `python -m json_manager.bids_rename_manager`) to edit BIDS filenames while keeping sidecar/data pairs aligned.

### Safety Checklist
- Always start with `--dry-run` to preview planned renames
- Keep backups enabled (default) to copy originals under `sourcedata/backup`
- Combine `--ses`, `--modality`, and `--file` filters to target specific subsets
- Prefer entity operations (`--remove-entity`, `--set-entity`) for BIDS-valid results

### Quick Help
```bash
# Show usage summary (same as --help)
./bids_rename_tool.sh

# Full help including options and examples
./bids_rename_tool.sh --help
```

### Common Workflows
```bash
# Remove an acquisition label from functional runs (and matching JSON/NIfTI)
./bids_rename_tool.sh -r /path/to/bids --modality func --remove-entity acq

# Add or update a description entity on anatomical files
./bids_rename_tool.sh -r /path/to/bids --modality anat --set-entity desc=T1wClean

# Strip a legacy suffix and then insert a new run label (dry-run first)
./bids_rename_tool.sh -r /path/to/bids --remove-substring "_pilot" --set-entity run=01 --dry-run

# Perform literal replacements before entity cleanup
./bids_rename_tool.sh -r /path/to/bids --replace "OldTask:newtask" --set-entity task=newtask
```

The tool automatically renames every file that shares the same base (e.g., `.nii.gz`, `.json`, `.tsv`, `.bval`, `.bvec`) so sidecars stay in sync. Operations are validated to ensure a `sub-` entity remains and that entity values/suffixes contain only BIDS-safe characters.

## 🛠️ Data Types & JSON Values

### String Values
```bash
--value '"string_value"'    # Note the quotes!
```

### Numeric Values
```bash
--value 2.0                 # Float
--value 42                  # Integer
```

### Boolean Values
```bash
--value true                # Boolean true
--value false               # Boolean false
```

### Arrays
```bash
--value '[1, 2, 3]'         # Number array
--value '["a", "b", "c"]'   # String array
--value '[0.0, 0.5, 1.0]'   # Float array
```

### Objects
```bash
--value '{"key": "value", "num": 42}'  # JSON object
```

## 🔍 Troubleshooting

### Common Issues

1. **"JSON decode error"**
   - Check that your JSON values are properly formatted
   - Use single quotes around JSON, double quotes inside: `'["item1", "item2"]'`

2. **"Permission denied"**
   - Make sure scripts are executable: `chmod +x bids_json_tool.sh`
   - Check file permissions on your BIDS directory

3. **"No files found"**
   - Verify the root path is correct
   - Check your file pattern matches existing files

4. **"Tag not found"**
   - Use `list` command to see available tags
   - Check if tag exists before trying to modify

### Getting Help

```bash
# General help
./bids_json_tool.sh help

# Command-specific help
./bids_json_tool.sh add --help
./bids_json_tool.sh remove --help
```

## 📊 Examples with Real BIDS Data

### Example 1: Complete Task Setup
```bash
# Setup for a resting state experiment
./bids_json_tool.sh add -r /data/bids_study --tag TaskName --value '"rest"' -p "*func*.json"
./bids_json_tool.sh add -r /data/bids_study --tag Instructions --value '"Keep your eyes closed and try not to think of anything in particular"' -p "*func*.json"
./bids_json_tool.sh add -r /data/bids_study --tag CogAtlasID --value '"trm_4c898c6e04c2a"' -p "*func*.json"
```

### Example 2: Fix Common Issues
```bash
# Remove problematic fields added by scanner software
./bids_json_tool.sh remove -r /data/bids_study --tag ProtocolName
./bids_json_tool.sh remove -r /data/bids_study --tag StudyInstanceUID

# Standardize naming
./bids_json_tool.sh replace -r /data/bids_study --tag SeriesDescription --search "ep2d_bold" --replace "task-rest_bold"
```

### Example 3: Batch Quality Control
```bash
# Check what tags exist
./bids_json_tool.sh list -r /data/bids_study

# Validate all files
./bids_json_tool.sh validate -r /data/bids_study

# Check specific modality
./bids_json_tool.sh list -r /data/bids_study -p "*func*.json"
```

## 🔄 Migration from Legacy Tools

If you were using the old `rename_json.sh`:

**Old way:**
```bash
./rename_json.sh -s "old_value" -r "new_value" -j "TagName" -f /path/to/bids
```

**New way:**
```bash
./bids_json_tool.sh replace -r /path/to/bids --tag TagName --search "old_value" --replace "new_value"
```

The new tool provides the same functionality plus much more!

## 📝 Notes

- **Backup Safety**: JSON files are automatically backed up (`.json.bak`) into `sourcedata/backup` unless `--no-backup` is used
- **BIDS Compliance**: Tool is designed to work with standard BIDS directory structures
- **Performance**: Efficiently processes large datasets with thousands of JSON files
- **Error Handling**: Robust error detection and reporting for malformed JSON files
- **Cross-Platform**: Works on macOS, Linux, and Windows (with appropriate shell)

## 🤝 Contributing

Found a bug or want to add a feature? Feel free to submit issues or pull requests to improve these BIDS tools!