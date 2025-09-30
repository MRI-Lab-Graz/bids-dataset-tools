#!/usr/bin/env python3
"""
BIDS JSON Manager - A comprehensive tool for managing JSON sidecar files in BIDS datasets

This tool provides easy-to-use functionality for:
- Adding new JSON tags/fields
- Removing existing JSON tags/fields
- Modifying values of existing JSON tags
- Validating JSON structure
- BIDS-aware operations

Author: BIDS Dataset Tools
License: MIT
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import re


class BIDSJSONManager:
    """Main class for managing BIDS JSON files"""
    
    def __init__(self, verbose: bool = False, dry_run: bool = False):
        self.verbose = verbose
        self.dry_run = dry_run
        self.processed_files = []
        self.error_files = []
        
    def log(self, message: str, level: str = "INFO") -> None:
        """Log messages with optional verbosity"""
        if self.verbose or level == "ERROR":
            prefix = f"[{level}]" if level != "INFO" else ""
            if self.dry_run and level == "INFO":
                prefix = "[DRY-RUN]"
            print(f"{prefix} {message}")
    
    def find_json_files(self, root_path: str, pattern: str = "*.json", 
                        session: Optional[str] = None, modality: Optional[str] = None,
                        filename_pattern: Optional[str] = None) -> List[Path]:
        """Find all JSON files in the given directory tree with optional BIDS-aware filtering"""
        root = Path(root_path)
        if not root.exists():
            raise FileNotFoundError(f"Directory not found: {root_path}")
        
        # Start with all JSON files
        json_files = list(root.rglob(pattern))
        self.log(f"Found {len(json_files)} JSON files before filtering")
        
        # Apply BIDS-specific filters
        filtered_files = []
        
        for file_path in json_files:
            # Convert to relative path for easier pattern matching
            try:
                rel_path = file_path.relative_to(root)
                path_parts = rel_path.parts
            except ValueError:
                # Skip files outside root directory
                continue
            
            # Session filtering (--ses)
            if session is not None:
                session_found = False
                for part in path_parts:
                    if part.startswith('ses-'):
                        # Try both string and zero-padded number formats
                        if part == f'ses-{session}':
                            session_found = True
                            break
                        # Try zero-padded format if session is numeric
                        try:
                            session_num = int(session)
                            if part == f'ses-{session_num:02d}':
                                session_found = True
                                break
                        except ValueError:
                            # session is not numeric, already checked string format above
                            pass
                if not session_found:
                    continue
            
            # Modality filtering (--anat, --func, etc.)
            if modality is not None:
                modality_found = False
                for part in path_parts:
                    if part == modality:
                        modality_found = True
                        break
                if not modality_found:
                    continue
            
            # Filename pattern filtering (--file)
            if filename_pattern is not None:
                import fnmatch
                filename = file_path.name
                if not fnmatch.fnmatch(filename, filename_pattern):
                    continue
            
            filtered_files.append(file_path)
        
        self.log(f"Found {len(filtered_files)} JSON files after filtering")
        if self.verbose and len(filtered_files) != len(json_files):
            self.log(f"  Filtered out {len(json_files) - len(filtered_files)} files")
            if session:
                self.log(f"  Session filter: ses-{session}")
            if modality:
                self.log(f"  Modality filter: {modality}")
            if filename_pattern:
                self.log(f"  Filename pattern: {filename_pattern}")
        
        return filtered_files
    
    def load_json_safely(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Safely load JSON file with error handling"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self.log(f"Invalid JSON in {file_path}: {e}", "ERROR")
            self.error_files.append(str(file_path))
            return None
        except Exception as e:
            self.log(f"Error reading {file_path}: {e}", "ERROR")
            self.error_files.append(str(file_path))
            return None
    
    def save_json_safely(self, file_path: Path, data: Dict[str, Any], backup: bool = True) -> bool:
        """Safely save JSON file with optional backup"""
        if self.dry_run:
            self.log(f"Would save changes to {file_path}")
            return True
        
        try:
            if backup:
                backup_path = file_path.with_suffix('.json.bak')
                if file_path.exists():
                    file_path.replace(backup_path)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.log(f"Error saving {file_path}: {e}", "ERROR")
            self.error_files.append(str(file_path))
            return False
    
    def add_tag(self, root_path: str, tag_name: str, tag_value: Any, 
                file_pattern: str = "*.json", overwrite: bool = False,
                session: Optional[str] = None, modality: Optional[str] = None,
                filename_pattern: Optional[str] = None) -> None:
        """Add a new tag to JSON files"""
        self.log(f"Adding tag '{tag_name}' with value '{tag_value}'")
        
        # Parse tag value (try to convert to appropriate type)
        parsed_value = self._parse_value(tag_value)
        
        json_files = self.find_json_files(root_path, file_pattern, session, modality, filename_pattern)
        
        for file_path in json_files:
            data = self.load_json_safely(file_path)
            if data is None:
                continue
            
            if tag_name in data and not overwrite:
                self.log(f"Tag '{tag_name}' already exists in {file_path}, skipping (use --overwrite to replace)")
                continue
            
            if self.dry_run:
                if tag_name in data:
                    self.log(f"Would update '{tag_name}': {data[tag_name]} -> {parsed_value} in {file_path}")
                else:
                    self.log(f"Would add '{tag_name}': {parsed_value} to {file_path}")
            
            data[tag_name] = parsed_value
            
            if self.save_json_safely(file_path, data):
                self.processed_files.append(str(file_path))
                if not self.dry_run:
                    self.log(f"Added tag to {file_path}")
    
    def remove_tag(self, root_path: str, tag_name: str, file_pattern: str = "*.json",
                   session: Optional[str] = None, modality: Optional[str] = None,
                   filename_pattern: Optional[str] = None) -> None:
        """Remove a tag from JSON files"""
        self.log(f"Removing tag '{tag_name}'")
        
        json_files = self.find_json_files(root_path, file_pattern, session, modality, filename_pattern)
        
        for file_path in json_files:
            data = self.load_json_safely(file_path)
            if data is None:
                continue
            
            if tag_name in data:
                if self.dry_run:
                    self.log(f"Would remove '{tag_name}': {data[tag_name]} from {file_path}")
                
                del data[tag_name]
                if self.save_json_safely(file_path, data):
                    self.processed_files.append(str(file_path))
                    if not self.dry_run:
                        self.log(f"Removed tag from {file_path}")
            else:
                self.log(f"Tag '{tag_name}' not found in {file_path}")
    
    def modify_tag(self, root_path: str, tag_name: str, new_value: Any, 
                   file_pattern: str = "*.json", create_if_missing: bool = False,
                   session: Optional[str] = None, modality: Optional[str] = None,
                   filename_pattern: Optional[str] = None) -> None:
        """Modify the value of an existing tag"""
        self.log(f"Modifying tag '{tag_name}' to value '{new_value}'")
        
        parsed_value = self._parse_value(new_value)
        json_files = self.find_json_files(root_path, file_pattern, session, modality, filename_pattern)
        
        for file_path in json_files:
            data = self.load_json_safely(file_path)
            if data is None:
                continue
            
            if tag_name in data:
                if self.dry_run:
                    self.log(f"Would modify '{tag_name}': {data[tag_name]} -> {parsed_value} in {file_path}")
                
                data[tag_name] = parsed_value
                if self.save_json_safely(file_path, data):
                    self.processed_files.append(str(file_path))
                    if not self.dry_run:
                        self.log(f"Modified tag in {file_path}")
            elif create_if_missing:
                if self.dry_run:
                    self.log(f"Would create '{tag_name}': {parsed_value} in {file_path}")
                
                data[tag_name] = parsed_value
                if self.save_json_safely(file_path, data):
                    self.processed_files.append(str(file_path))
                    if not self.dry_run:
                        self.log(f"Created and set tag in {file_path}")
            else:
                self.log(f"Tag '{tag_name}' not found in {file_path} (use --create to add missing tags)")
    
    def replace_string_in_tag(self, root_path: str, tag_name: str, search_str: str, 
                              replace_str: str, file_pattern: str = "*.json",
                              session: Optional[str] = None, modality: Optional[str] = None,
                              filename_pattern: Optional[str] = None) -> None:
        """Replace string values within specific tags (legacy functionality)"""
        self.log(f"Replacing '{search_str}' with '{replace_str}' in tag '{tag_name}'")
        
        json_files = self.find_json_files(root_path, file_pattern, session, modality, filename_pattern)
        
        for file_path in json_files:
            data = self.load_json_safely(file_path)
            if data is None:
                continue
            
            if tag_name in data:
                if isinstance(data[tag_name], str):
                    old_value = data[tag_name]
                    data[tag_name] = old_value.replace(search_str, replace_str)
                    if old_value != data[tag_name]:
                        if self.save_json_safely(file_path, data):
                            self.processed_files.append(str(file_path))
                            self.log(f"Updated string in {file_path}")
                elif isinstance(data[tag_name], list):
                    # Handle arrays of strings
                    modified = False
                    for i, item in enumerate(data[tag_name]):
                        if isinstance(item, str):
                            new_item = item.replace(search_str, replace_str)
                            if new_item != item:
                                data[tag_name][i] = new_item
                                modified = True
                    if modified:
                        if self.save_json_safely(file_path, data):
                            self.processed_files.append(str(file_path))
                            self.log(f"Updated array strings in {file_path}")
    
    def list_tags(self, root_path: str, file_pattern: str = "*.json",
                  session: Optional[str] = None, modality: Optional[str] = None,
                  filename_pattern: Optional[str] = None) -> None:
        """List all unique tags found in JSON files"""
        self.log("Scanning for all JSON tags...")
        
        all_tags = set()
        json_files = self.find_json_files(root_path, file_pattern, session, modality, filename_pattern)
        
        for file_path in json_files:
            data = self.load_json_safely(file_path)
            if data is None:
                continue
            all_tags.update(data.keys())
        
        print(f"\nFound {len(all_tags)} unique tags:")
        for tag in sorted(all_tags):
            print(f"  - {tag}")
    
    def validate_files(self, root_path: str, file_pattern: str = "*.json",
                       session: Optional[str] = None, modality: Optional[str] = None,
                       filename_pattern: Optional[str] = None) -> None:
        """Validate JSON structure of files"""
        self.log("Validating JSON files...")
        
        json_files = self.find_json_files(root_path, file_pattern, session, modality, filename_pattern)
        valid_files = 0
        
        for file_path in json_files:
            data = self.load_json_safely(file_path)
            if data is not None:
                valid_files += 1
        
        print(f"\nValidation results:")
        print(f"  Total files: {len(json_files)}")
        print(f"  Valid files: {valid_files}")
        print(f"  Invalid files: {len(self.error_files)}")
        
        if self.error_files:
            print(f"\nFiles with errors:")
            for error_file in self.error_files:
                print(f"  - {error_file}")
    
    def copy_tags(self, root_path: str, source_pattern: str, target_pattern: str, 
                  tag_names: List[str], file_pattern: str = "*.json",
                  session: Optional[str] = None, modality: Optional[str] = None,
                  filename_pattern: Optional[str] = None, overwrite: bool = False) -> None:
        """Copy specific tags from source files to target files"""
        self.log(f"Copying tags {tag_names} from {source_pattern} to {target_pattern}")
        
        # Find source files
        source_files = self.find_json_files(root_path, source_pattern, session, modality, filename_pattern)
        target_files = self.find_json_files(root_path, target_pattern, session, modality, filename_pattern)
        
        if not source_files:
            self.log("No source files found", "ERROR")
            return
        
        if not target_files:
            self.log("No target files found", "ERROR")
            return
        
        # Collect tags from source files
        collected_tags = {}
        for source_file in source_files:
            data = self.load_json_safely(source_file)
            if data is None:
                continue
            
            for tag_name in tag_names:
                if tag_name in data and tag_name not in collected_tags:
                    collected_tags[tag_name] = data[tag_name]
                    self.log(f"Collected '{tag_name}': {data[tag_name]} from {source_file}")
        
        if not collected_tags:
            self.log(f"No tags {tag_names} found in source files", "ERROR")
            return
        
        # Apply tags to target files
        for target_file in target_files:
            data = self.load_json_safely(target_file)
            if data is None:
                continue
            
            modified = False
            for tag_name, tag_value in collected_tags.items():
                if tag_name in data and not overwrite:
                    self.log(f"Tag '{tag_name}' already exists in {target_file}, skipping")
                    continue
                
                if self.dry_run:
                    if tag_name in data:
                        self.log(f"Would update '{tag_name}': {data[tag_name]} -> {tag_value} in {target_file}")
                    else:
                        self.log(f"Would add '{tag_name}': {tag_value} to {target_file}")
                
                data[tag_name] = tag_value
                modified = True
            
            if modified:
                if self.save_json_safely(target_file, data):
                    self.processed_files.append(str(target_file))
                    if not self.dry_run:
                        self.log(f"Copied tags to {target_file}")
    
    def diff_tags(self, root_path: str, pattern1: str, pattern2: str,
                  file_pattern: str = "*.json", session: Optional[str] = None, 
                  modality: Optional[str] = None, filename_pattern: Optional[str] = None) -> None:
        """Compare tags between two sets of files"""
        self.log(f"Comparing tags between {pattern1} and {pattern2}")
        
        files1 = self.find_json_files(root_path, pattern1, session, modality, filename_pattern)
        files2 = self.find_json_files(root_path, pattern2, session, modality, filename_pattern)
        
        # Collect all tags from both sets
        tags1 = set()
        tags2 = set()
        
        for file_path in files1:
            data = self.load_json_safely(file_path)
            if data:
                tags1.update(data.keys())
        
        for file_path in files2:
            data = self.load_json_safely(file_path)
            if data:
                tags2.update(data.keys())
        
        # Show differences
        only_in_1 = tags1 - tags2
        only_in_2 = tags2 - tags1
        common = tags1 & tags2
        
        print(f"\nTag Comparison Results:")
        print(f"  Files matching '{pattern1}': {len(files1)} files, {len(tags1)} unique tags")
        print(f"  Files matching '{pattern2}': {len(files2)} files, {len(tags2)} unique tags")
        print(f"  Common tags: {len(common)}")
        
        if only_in_1:
            print(f"\n  Tags only in '{pattern1}':")
            for tag in sorted(only_in_1):
                print(f"    - {tag}")
        
        if only_in_2:
            print(f"\n  Tags only in '{pattern2}':")
            for tag in sorted(only_in_2):
                print(f"    - {tag}")
        
        if common:
            print(f"\n  Common tags:")
            for tag in sorted(common):
                print(f"    - {tag}")
    
    def apply_template(self, root_path: str, template_name: str, file_pattern: str = "*.json",
                      session: Optional[str] = None, modality: Optional[str] = None,
                      filename_pattern: Optional[str] = None, overwrite: bool = False) -> None:
        """Apply BIDS template with predefined tags"""
        
        # Define BIDS templates
        templates = {
            'func-rest': {
                'TaskName': 'rest',
                'Instructions': 'Keep your eyes open and try not to think of anything in particular'
            },
            'func-task': {
                'TaskName': 'CHANGEME',
                'Instructions': 'CHANGEME - Add task instructions here'
            },
            'anat-T1w': {
                'ScanningSequence': 'GR',
                'SequenceVariant': 'MP'
            },
            'anat-T2w': {
                'ScanningSequence': 'SE',
                'EchoTrainLength': 'CHANGEME'
            },
            'fmap-magnitude': {
                'IntendedFor': 'CHANGEME',
                'Units': 'Hz'
            },
            'dwi-basic': {
                'PhaseEncodingDirection': 'CHANGEME',
                'TotalReadoutTime': 'CHANGEME'
            }
        }
        
        if template_name not in templates:
            self.log(f"Unknown template '{template_name}'. Available templates: {list(templates.keys())}", "ERROR")
            return
        
        template_data = templates[template_name]
        self.log(f"Applying template '{template_name}' with tags: {list(template_data.keys())}")
        
        json_files = self.find_json_files(root_path, file_pattern, session, modality, filename_pattern)
        
        for file_path in json_files:
            data = self.load_json_safely(file_path)
            if data is None:
                continue
            
            modified = False
            for tag_name, tag_value in template_data.items():
                if tag_name in data and not overwrite:
                    self.log(f"Tag '{tag_name}' already exists in {file_path}, skipping")
                    continue
                
                if self.dry_run:
                    if tag_name in data:
                        self.log(f"Would update '{tag_name}': {data[tag_name]} -> {tag_value} in {file_path}")
                    else:
                        self.log(f"Would add '{tag_name}': {tag_value} to {file_path}")
                
                data[tag_name] = tag_value
                modified = True
            
            if modified:
                if self.save_json_safely(file_path, data):
                    self.processed_files.append(str(file_path))
                    if not self.dry_run:
                        self.log(f"Applied template to {file_path}")
    
    def list_templates(self) -> None:
        """List available BIDS templates"""
        templates = {
            'func-rest': 'Resting-state functional MRI',
            'func-task': 'Task-based functional MRI (requires customization)',
            'anat-T1w': 'T1-weighted anatomical MRI',
            'anat-T2w': 'T2-weighted anatomical MRI', 
            'fmap-magnitude': 'Field map magnitude images',
            'dwi-basic': 'Diffusion-weighted imaging (basic)'
        }
        
        print("\nAvailable BIDS Templates:")
        for name, description in templates.items():
            print(f"  {name:<15} - {description}")
    def check_compliance(self, root_path: str, file_pattern: str = "*.json",
                        session: Optional[str] = None, modality: Optional[str] = None,
                        filename_pattern: Optional[str] = None) -> None:
        """Check BIDS compliance of JSON files"""
        
        # Define BIDS required and recommended fields by modality
        bids_spec = {
            'func': {
                'required': ['RepetitionTime', 'TaskName'],
                'recommended': ['EchoTime', 'FlipAngle', 'SliceTiming'],
                'forbidden': [],
                'conditional': {
                    'SliceTiming': 'Required if not using slice timing correction'
                }
            },
            'anat': {
                'required': [],
                'recommended': ['EchoTime', 'FlipAngle', 'RepetitionTime'],
                'forbidden': ['TaskName', 'SliceTiming'],
                'conditional': {}
            },
            'fmap': {
                'required': ['IntendedFor'],
                'recommended': ['EchoTime1', 'EchoTime2', 'Units'],
                'forbidden': ['TaskName', 'SliceTiming'],
                'conditional': {
                    'EchoTime1': 'Required for phase difference maps',
                    'EchoTime2': 'Required for phase difference maps'
                }
            },
            'dwi': {
                'required': ['PhaseEncodingDirection', 'TotalReadoutTime'],
                'recommended': ['EchoTime', 'FlipAngle'],
                'forbidden': ['TaskName', 'SliceTiming'],
                'conditional': {}
            }
        }
        
        self.log("Checking BIDS compliance...")
        json_files = self.find_json_files(root_path, file_pattern, session, modality, filename_pattern)
        
        compliance_results = {
            'total_files': 0,
            'compliant_files': 0,
            'issues': [],
            'by_modality': {}
        }
        
        for file_path in json_files:
            data = self.load_json_safely(file_path)
            if data is None:
                continue
            
            compliance_results['total_files'] += 1
            
            # Determine modality from file path
            file_modality = self._detect_modality(file_path)
            if file_modality not in compliance_results['by_modality']:
                compliance_results['by_modality'][file_modality] = {
                    'count': 0, 'compliant': 0, 'issues': []
                }
            
            compliance_results['by_modality'][file_modality]['count'] += 1
            
            if file_modality in bids_spec:
                spec = bids_spec[file_modality]
                file_issues = []
                
                # Check required fields
                for required_field in spec['required']:
                    if required_field not in data:
                        issue = f"Missing required field '{required_field}'"
                        file_issues.append(issue)
                        compliance_results['issues'].append(f"{file_path}: {issue}")
                
                # Check forbidden fields
                for forbidden_field in spec['forbidden']:
                    if forbidden_field in data:
                        issue = f"Contains forbidden field '{forbidden_field}'"
                        file_issues.append(issue)
                        compliance_results['issues'].append(f"{file_path}: {issue}")
                
                # Check for common BIDS issues
                if 'TaskName' in data and data['TaskName'] in ['CHANGEME', '', None]:
                    issue = "TaskName contains placeholder value"
                    file_issues.append(issue)
                    compliance_results['issues'].append(f"{file_path}: {issue}")
                
                # Check for suspicious values
                for key, value in data.items():
                    if isinstance(value, str) and 'CHANGEME' in value:
                        issue = f"Field '{key}' contains placeholder 'CHANGEME'"
                        file_issues.append(issue)
                        compliance_results['issues'].append(f"{file_path}: {issue}")
                
                if not file_issues:
                    compliance_results['compliant_files'] += 1
                    compliance_results['by_modality'][file_modality]['compliant'] += 1
                else:
                    compliance_results['by_modality'][file_modality]['issues'].extend(file_issues)
        
        # Print compliance report
        self._print_compliance_report(compliance_results)
    
    def _detect_modality(self, file_path: Path) -> str:
        """Detect BIDS modality from file path"""
        path_str = str(file_path)
        if '/func/' in path_str or 'task-' in path_str:
            return 'func'
        elif '/anat/' in path_str:
            return 'anat'
        elif '/fmap/' in path_str:
            return 'fmap'
        elif '/dwi/' in path_str:
            return 'dwi'
        elif '/perf/' in path_str:
            return 'perf'
        elif '/meg/' in path_str:
            return 'meg'
        elif '/eeg/' in path_str:
            return 'eeg'
        elif '/ieeg/' in path_str:
            return 'ieeg'
        elif '/beh/' in path_str:
            return 'beh'
        else:
            return 'unknown'
    
    def _print_compliance_report(self, results: Dict[str, Any]) -> None:
        """Print formatted compliance report"""
        print(f"\n{'='*60}")
        print(f"BIDS COMPLIANCE REPORT")
        print(f"{'='*60}")
        
        total = results['total_files']
        compliant = results['compliant_files']
        compliance_rate = (compliant / total * 100) if total > 0 else 0
        
        print(f"Overall Compliance: {compliant}/{total} files ({compliance_rate:.1f}%)")
        
        if results['by_modality']:
            print(f"\nBy Modality:")
            for modality, stats in results['by_modality'].items():
                mod_rate = (stats['compliant'] / stats['count'] * 100) if stats['count'] > 0 else 0
                print(f"  {modality:8}: {stats['compliant']:3}/{stats['count']:3} files ({mod_rate:5.1f}%)")
        
        if results['issues']:
            print(f"\nIssues Found ({len(results['issues'])}):")
            for issue in sorted(set(results['issues']))[:20]:  # Show first 20 unique issues
                print(f"  ❌ {issue}")
            
            if len(results['issues']) > 20:
                print(f"  ... and {len(results['issues']) - 20} more issues")
        else:
            print(f"\n✅ No compliance issues found!")
        
        print(f"{'='*60}")
    
    def map_tags(self, root_path: str, mapping: Dict[str, str], file_pattern: str = "*.json",
                 session: Optional[str] = None, modality: Optional[str] = None,
                 filename_pattern: Optional[str] = None, delete_source: bool = False) -> None:
        """Map/rename tags according to provided mapping"""
        self.log(f"Mapping tags: {mapping}")
        
        json_files = self.find_json_files(root_path, file_pattern, session, modality, filename_pattern)
        
        for file_path in json_files:
            data = self.load_json_safely(file_path)
            if data is None:
                continue
            
            modified = False
            for old_tag, new_tag in mapping.items():
                if old_tag in data:
                    if self.dry_run:
                        self.log(f"Would map '{old_tag}' -> '{new_tag}': {data[old_tag]} in {file_path}")
                    
                    # Copy value to new tag
                    data[new_tag] = data[old_tag]
                    
                    # Optionally delete source tag
                    if delete_source:
                        del data[old_tag]
                        if self.dry_run:
                            self.log(f"Would delete source tag '{old_tag}' from {file_path}")
                    
                    modified = True
            
            if modified:
                if self.save_json_safely(file_path, data):
                    self.processed_files.append(str(file_path))
                    if not self.dry_run:
                        self.log(f"Mapped tags in {file_path}")
    
    def show_statistics(self, root_path: str, file_pattern: str = "*.json",
                       session: Optional[str] = None, modality: Optional[str] = None,
                       filename_pattern: Optional[str] = None, detailed: bool = False) -> None:
        """Show statistics about tag usage and values across dataset"""
        self.log("Analyzing dataset statistics...")
        
        json_files = self.find_json_files(root_path, file_pattern, session, modality, filename_pattern)
        
        # Collect all data
        tag_stats = {}
        file_count = 0
        
        for file_path in json_files:
            data = self.load_json_safely(file_path)
            if data is None:
                continue
            
            file_count += 1
            modality = self._detect_modality(file_path)
            
            for tag, value in data.items():
                if tag not in tag_stats:
                    tag_stats[tag] = {
                        'count': 0,
                        'values': {},
                        'modalities': set(),
                        'types': set()
                    }
                
                tag_stats[tag]['count'] += 1
                tag_stats[tag]['modalities'].add(modality)
                tag_stats[tag]['types'].add(type(value).__name__)
                
                # Track value frequencies
                value_str = str(value)
                if value_str not in tag_stats[tag]['values']:
                    tag_stats[tag]['values'][value_str] = 0
                tag_stats[tag]['values'][value_str] += 1
        
        # Print statistics
        self._print_statistics_report(tag_stats, file_count, detailed)
    
    def _print_statistics_report(self, tag_stats: Dict[str, Any], file_count: int, detailed: bool) -> None:
        """Print formatted statistics report"""
        print(f"\n{'='*80}")
        print(f"DATASET STATISTICS")
        print(f"{'='*80}")
        print(f"Total JSON files analyzed: {file_count}")
        print(f"Total unique tags found: {len(tag_stats)}")
        
        # Sort tags by frequency
        sorted_tags = sorted(tag_stats.items(), key=lambda x: x[1]['count'], reverse=True)
        
        print(f"\nTag Usage Summary:")
        print(f"{'Tag Name':<25} {'Count':<8} {'Coverage':<10} {'Modalities':<20} {'Types'}")
        print(f"{'-'*80}")
        
        for tag, stats in sorted_tags:
            coverage = f"{stats['count']}/{file_count}"
            coverage_pct = f"({stats['count']/file_count*100:.1f}%)"
            modalities = ','.join(sorted(stats['modalities']))[:18]
            types = ','.join(sorted(stats['types']))
            
            print(f"{tag:<25} {stats['count']:<8} {coverage:<10} {modalities:<20} {types}")
        
        if detailed:
            print(f"\nDetailed Value Distributions:")
            print(f"{'-'*80}")
            
            for tag, stats in sorted_tags[:10]:  # Show top 10 tags
                print(f"\n{tag} (appears in {stats['count']} files):")
                
                # Sort values by frequency
                sorted_values = sorted(stats['values'].items(), 
                                     key=lambda x: x[1], reverse=True)
                
                for value, count in sorted_values[:5]:  # Show top 5 values
                    pct = count / stats['count'] * 100
                    value_display = value[:50] + "..." if len(value) > 50 else value
                    print(f"  {value_display:<30} {count:>3} files ({pct:5.1f}%)")
                
                if len(sorted_values) > 5:
                    print(f"  ... and {len(sorted_values) - 5} more unique values")
        
        print(f"\n{'='*80}")
        
        return
        """Parse string value to appropriate Python type"""
        # Try to parse as JSON first (handles numbers, booleans, arrays, objects)
        try:
            return json.loads(value_str)
        except json.JSONDecodeError:
            # If JSON parsing fails, treat as string
            return value_str
    
    def print_summary(self) -> None:
        """Print operation summary"""
        if self.dry_run:
            print(f"\nDry-Run Summary (NO CHANGES MADE):")
        else:
            print(f"\nOperation Summary:")
        print(f"  Files processed: {len(self.processed_files)}")
        print(f"  Files with errors: {len(self.error_files)}")
        
        if self.error_files:
            print(f"\nFiles with errors:")
            for error_file in self.error_files:
                print(f"  - {error_file}")


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    # Create parent parser with common arguments
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('--root', '-r', required=True, 
                              help='Root directory of BIDS dataset')
    parent_parser.add_argument('--pattern', '-p', default='*.json',
                              help='File pattern to match (default: *.json)')
    parent_parser.add_argument('--verbose', '-v', action='store_true',
                              help='Enable verbose output')
    parent_parser.add_argument('--no-backup', action='store_true',
                              help='Skip creating backup files')
    parent_parser.add_argument('--dry-run', '-n', action='store_true',
                              help='Preview operations without making changes')
    
    # BIDS-specific filtering arguments
    parent_parser.add_argument('--ses', '--session', type=str, metavar='SESSION',
                              help='Target specific session (e.g., --ses 1 or --ses 01)')
    parent_parser.add_argument('--anat', action='store_const', const='anat', dest='modality',
                              help='Target anatomical data only')
    parent_parser.add_argument('--func', action='store_const', const='func', dest='modality',
                              help='Target functional data only')
    parent_parser.add_argument('--fmap', action='store_const', const='fmap', dest='modality',
                              help='Target field map data only')
    parent_parser.add_argument('--dwi', action='store_const', const='dwi', dest='modality',
                              help='Target diffusion data only')
    parent_parser.add_argument('--perf', action='store_const', const='perf', dest='modality',
                              help='Target perfusion data only')
    parent_parser.add_argument('--meg', action='store_const', const='meg', dest='modality',
                              help='Target MEG data only')
    parent_parser.add_argument('--eeg', action='store_const', const='eeg', dest='modality',
                              help='Target EEG data only')
    parent_parser.add_argument('--ieeg', action='store_const', const='ieeg', dest='modality',
                              help='Target iEEG data only')
    parent_parser.add_argument('--beh', action='store_const', const='beh', dest='modality',
                              help='Target behavioral data only')
    parent_parser.add_argument('--file', '--filename', type=str, metavar='PATTERN',
                              help='Target files matching filename pattern (e.g., --file "*rest*")')
    
    # Main parser
    parser = argparse.ArgumentParser(
        description="BIDS JSON Manager - Manage JSON sidecar files in BIDS datasets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic operations
  %(prog)s add --root /path/to/bids --tag TaskName --value "rest"
  %(prog)s remove --root /path/to/bids --tag SliceTiming
  %(prog)s modify --root /path/to/bids --tag RepetitionTime --value 2.0
  
  # BIDS-aware filtering examples
  %(prog)s add --root /path/to/bids --tag TaskName --value "faces" --func
  %(prog)s remove --root /path/to/bids --tag EchoTime --anat
  %(prog)s modify --root /path/to/bids --tag PhaseEncodingDirection --value "j-" --fmap
  
  # Session-specific operations
  %(prog)s add --root /path/to/bids --tag Instructions --value "Keep eyes closed" --ses 1
  %(prog)s list --root /path/to/bids --ses 01 --func
  
  # Filename pattern targeting
  %(prog)s add --root /path/to/bids --tag TaskName --value "rest" --file "*rest*"
  %(prog)s remove --root /path/to/bids --tag SliceTiming --file "*bold*"
  
  # Combined filtering
  %(prog)s modify --root /path/to/bids --tag RepetitionTime --value 2.5 --ses 2 --func --file "*task-rest*"
  
  # Legacy string replacement
  %(prog)s replace --root /path/to/bids --tag SeriesDescription --search "old" --replace "new"
  
  # Validation and listing
  %(prog)s validate --root /path/to/bids --dwi
  %(prog)s list --root /path/to/bids --anat --ses 1
        """
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new tag to JSON files', 
                                      parents=[parent_parser])
    add_parser.add_argument('--tag', required=True, help='Tag name to add')
    add_parser.add_argument('--value', required=True, help='Tag value (JSON format)')
    add_parser.add_argument('--overwrite', action='store_true',
                           help='Overwrite existing tags')
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove a tag from JSON files',
                                         parents=[parent_parser])
    remove_parser.add_argument('--tag', required=True, help='Tag name to remove')
    
    # Modify command
    modify_parser = subparsers.add_parser('modify', help='Modify existing tag values',
                                         parents=[parent_parser])
    modify_parser.add_argument('--tag', required=True, help='Tag name to modify')
    modify_parser.add_argument('--value', required=True, help='New tag value (JSON format)')
    modify_parser.add_argument('--create', action='store_true',
                              help='Create tag if it doesn\'t exist')
    
    # Replace command (legacy)
    replace_parser = subparsers.add_parser('replace', help='Replace string in tag values (legacy)',
                                          parents=[parent_parser])
    replace_parser.add_argument('--tag', required=True, help='Tag name to search in')
    replace_parser.add_argument('--search', required=True, help='String to search for')
    replace_parser.add_argument('--replace', required=True, help='Replacement string')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all tags in JSON files',
                                       parents=[parent_parser])
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate JSON file structure',
                                           parents=[parent_parser])
    
    # Copy-tags command
    copy_parser = subparsers.add_parser('copy-tags', help='Copy tags from source to target files',
                                       parents=[parent_parser])
    copy_parser.add_argument('--from-pattern', required=True, 
                            help='Source file pattern to copy tags from')
    copy_parser.add_argument('--to-pattern', required=True,
                            help='Target file pattern to copy tags to')
    copy_parser.add_argument('--tags', required=True, nargs='+',
                            help='Tag names to copy (space-separated)')
    copy_parser.add_argument('--overwrite', action='store_true',
                            help='Overwrite existing tags in target files')
    
    # Diff command
    diff_parser = subparsers.add_parser('diff', help='Compare tags between two sets of files',
                                       parents=[parent_parser])
    diff_parser.add_argument('--pattern1', required=True,
                            help='First file pattern to compare')
    diff_parser.add_argument('--pattern2', required=True,
                            help='Second file pattern to compare')
    
    # Template command
    template_parser = subparsers.add_parser('template', help='Apply BIDS template configurations',
                                           parents=[parent_parser])
    template_parser.add_argument('--name', required=True,
                                help='Template name to apply')
    template_parser.add_argument('--overwrite', action='store_true',
                                help='Overwrite existing tags')
    
    # List-templates command  
    list_templates_parser = subparsers.add_parser('list-templates', 
                                                 help='List available BIDS templates')
    
    # Compliance check command
    compliance_parser = subparsers.add_parser('check-compliance', 
                                            help='Check BIDS compliance of JSON files',
                                            parents=[parent_parser])
    
    # Map tags command
    map_parser = subparsers.add_parser('map-tags', help='Rename/map tags systematically',
                                      parents=[parent_parser])
    map_parser.add_argument('--mapping', required=True, 
                           help='Tag mapping in format "old1:new1,old2:new2"')
    map_parser.add_argument('--delete-source', action='store_true',
                           help='Delete original tags after mapping')
    
    # Statistics command
    stats_parser = subparsers.add_parser('stats', help='Show dataset statistics',
                                        parents=[parent_parser])
    stats_parser.add_argument('--detailed', action='store_true',
                             help='Show detailed value distributions')
    
    return parser


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        # Handle list-templates separately since it doesn't need most arguments
        if args.command == 'list-templates':
            simple_manager = BIDSJSONManager()
            simple_manager.list_templates()
            return
        
        # For all other commands, create manager with full arguments
        manager = BIDSJSONManager(verbose=args.verbose, dry_run=args.dry_run)
        backup = not args.no_backup
        
        # Extract filtering parameters
        session = getattr(args, 'ses', None)
        modality = getattr(args, 'modality', None)
        filename_pattern = getattr(args, 'file', None)
        
        if args.command == 'add':
            manager.add_tag(args.root, args.tag, args.value, 
                           args.pattern, args.overwrite, session, modality, filename_pattern)
        elif args.command == 'remove':
            manager.remove_tag(args.root, args.tag, args.pattern, session, modality, filename_pattern)
        elif args.command == 'modify':
            manager.modify_tag(args.root, args.tag, args.value, 
                              args.pattern, args.create, session, modality, filename_pattern)
        elif args.command == 'replace':
            manager.replace_string_in_tag(args.root, args.tag, args.search, 
                                         args.replace, args.pattern, session, modality, filename_pattern)
        elif args.command == 'list':
            manager.list_tags(args.root, args.pattern, session, modality, filename_pattern)
        elif args.command == 'validate':
            manager.validate_files(args.root, args.pattern, session, modality, filename_pattern)
        elif args.command == 'copy-tags':
            manager.copy_tags(args.root, args.from_pattern, args.to_pattern, args.tags,
                             args.pattern, session, modality, filename_pattern, args.overwrite)
        elif args.command == 'diff':
            manager.diff_tags(args.root, args.pattern1, args.pattern2,
                             args.pattern, session, modality, filename_pattern)
        elif args.command == 'template':
            manager.apply_template(args.root, args.name, args.pattern, 
                                  session, modality, filename_pattern, args.overwrite)
        elif args.command == 'check-compliance':
            manager.check_compliance(args.root, args.pattern, session, modality, filename_pattern)
        elif args.command == 'map-tags':
            # Parse mapping string "old1:new1,old2:new2" into dict
            mapping = {}
            for pair in args.mapping.split(','):
                if ':' in pair:
                    old, new = pair.strip().split(':', 1)
                    mapping[old.strip()] = new.strip()
            manager.map_tags(args.root, mapping, args.pattern, session, modality, 
                           filename_pattern, args.delete_source)
        elif args.command == 'stats':
            manager.show_statistics(args.root, args.pattern, session, modality, 
                                  filename_pattern, args.detailed)
        
        manager.print_summary()
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()