#!/usr/bin/env python3
"""BIDS Rename Manager - safely rename BIDS files with entity-aware logic"""

from __future__ import annotations

import argparse
import re
import shutil
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


CANONICAL_ENTITY_ORDER = [
    "sub", "ses", "task", "acq", "ce", "dir", "rec", "run", "echo",
    "flip", "inv", "mt", "part", "recording", "space", "split", "desc",
    "label"
]

ALLOWED_SUFFIX_PATTERN = re.compile(r"^[A-Za-z0-9]+$")
ALLOWED_ENTITY_VALUE_PATTERN = re.compile(r"^[A-Za-z0-9]+$")


class BIDSFileRenamer:
    """Rename BIDS files while keeping dataset structure consistent"""

    def __init__(self, verbose: bool = False, dry_run: bool = False):
        self.verbose = verbose
        self.dry_run = dry_run
        self.remove_substrings: List[str] = []
        self.replace_pairs: List[Tuple[str, str]] = []
        self.remove_entities: List[str] = []
        self.set_entities: Dict[str, str] = {}
        self.processed_files: List[str] = []
        self.error_files: List[str] = []
        self.backup_enabled: bool = True
        self.backup_root: Optional[Path] = None
        self.backup_base_dirname: Path = Path("sourcedata") / "backup"
        self.dataset_root: Optional[Path] = None

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------
    def log(self, message: str, level: str = "INFO") -> None:
        if self.verbose or level == "ERROR":
            prefix = f"[{level}]" if level != "INFO" else ""
            if self.dry_run and level == "INFO":
                prefix = "[DRY-RUN]"
            print(f"{prefix} {message}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def rename(self, root_path: str, pattern: str = "*", session: Optional[str] = None,
               modality: Optional[str] = None, filename_pattern: Optional[str] = None) -> None:
        root_input = Path(root_path)
        if not root_input.exists():
            raise FileNotFoundError(f"Directory not found: {root_path}")
        root = root_input.resolve()
        self.dataset_root = root
        self.backup_root = root

        groups = self._find_file_groups(root, pattern, session, modality, filename_pattern)
        planned_moves: List[Tuple[Path, Path]] = []

        for (parent, base_name), files in groups.items():
            try:
                new_base_name = self._transform_base_name(base_name)
            except ValueError as exc:
                self.log(f"Skipping {parent / base_name}: {exc}", "ERROR")
                self.error_files.append(str(parent / base_name))
                continue

            if new_base_name == base_name:
                continue

            self._validate_bids_name(new_base_name)

            for rel_path in files:
                ext = self._collect_suffix(rel_path.name)
                new_relative = parent / f"{new_base_name}{ext}"
                planned_moves.append((rel_path, new_relative))

        self._ensure_no_collisions(root, planned_moves)
        self._execute_moves(root, planned_moves)

    # ------------------------------------------------------------------
    # Group discovery
    # ------------------------------------------------------------------
    def _find_file_groups(self, root: Path, pattern: str, session: Optional[str],
                           modality: Optional[str], filename_pattern: Optional[str]) -> Dict[Tuple[Path, str], List[Path]]:
        groups: Dict[Tuple[Path, str], List[Path]] = defaultdict(list)

        for file_path in root.rglob(pattern):
            if not file_path.is_file():
                continue
            if self._is_in_backup_area(root, file_path):
                continue

            rel_path = file_path.relative_to(root)
            if not self._passes_filters(rel_path, session, modality, filename_pattern):
                continue

            base_name = self._strip_all_suffixes(rel_path.name)
            parent = rel_path.parent
            groups[(parent, base_name)].append(rel_path)

        if self.verbose:
            total_files = sum(len(files) for files in groups.values())
            self.log(f"Identified {len(groups)} base groups covering {total_files} files")

        return groups

    def _passes_filters(self, rel_path: Path, session: Optional[str], modality: Optional[str],
                        filename_pattern: Optional[str]) -> bool:
        path_parts = rel_path.parts

        if session is not None:
            if not any(part.startswith("ses-") and self._session_matches(part, session) for part in path_parts):
                return False

        if modality is not None:
            if modality not in path_parts:
                return False

        if filename_pattern is not None:
            import fnmatch
            if not fnmatch.fnmatch(rel_path.name, filename_pattern):
                return False

        return True

    def _session_matches(self, part: str, session: str) -> bool:
        if part == f"ses-{session}":
            return True
        try:
            return part == f"ses-{int(session):02d}"
        except ValueError:
            return False

    def _is_in_backup_area(self, root: Path, file_path: Path) -> bool:
        backup_rel = file_path.relative_to(root)
        backup_parts = self.backup_base_dirname.parts
        return backup_rel.parts[:len(backup_parts)] == backup_parts

    # ------------------------------------------------------------------
    # Base name transformations
    # ------------------------------------------------------------------
    def _transform_base_name(self, base_name: str) -> str:
        updated = base_name

        for removal in self.remove_substrings:
            updated = updated.replace(removal, "")

        for old, new in self.replace_pairs:
            updated = updated.replace(old, new)

        entities, suffix = self._parse_bids_name(updated)

        for entity in self.remove_entities:
            if entity == "sub":
                raise ValueError("Cannot remove mandatory 'sub' entity")
            entities.pop(entity, None)

        for entity, value in self.set_entities.items():
            if not value:
                raise ValueError(f"Entity '{entity}' requires a non-empty value")
            entities = self._insert_or_update_entity(entities, entity, value)

        rebuilt = self._build_bids_name(entities, suffix)
        rebuilt = self._normalize_base(rebuilt)
        return rebuilt

    def _parse_bids_name(self, base_name: str) -> Tuple[OrderedDict[str, str], str]:
        parts = [p for p in base_name.split("_") if p]
        if not parts:
            raise ValueError("Empty filename")

        suffix = parts[-1]
        entities = OrderedDict()

        for part in parts[:-1]:
            if "-" not in part:
                raise ValueError(f"Segment '{part}' is missing '-' separator")
            key, value = part.split("-", 1)
            if not key or not value:
                raise ValueError(f"Invalid BIDS entity expression '{part}'")
            entities[key] = value

        if "sub" not in entities:
            raise ValueError("Filename is missing required 'sub' entity")

        return entities, suffix

    def _insert_or_update_entity(self, entities: OrderedDict[str, str],
                                 entity: str, value: str) -> OrderedDict[str, str]:
        sanitized_value = value.strip()
        if not ALLOWED_ENTITY_VALUE_PATTERN.fullmatch(sanitized_value):
            raise ValueError(f"Entity value '{value}' contains invalid characters")

        if entity in entities:
            entities[entity] = sanitized_value
            return entities

        new_entities: "OrderedDict[str, str]" = OrderedDict()
        inserted = False
        target_index = self._entity_order_index(entity)

        for existing_key, existing_value in entities.items():
            if not inserted and target_index < self._entity_order_index(existing_key):
                new_entities[entity] = sanitized_value
                inserted = True
            new_entities[existing_key] = existing_value

        if not inserted:
            new_entities[entity] = sanitized_value

        return new_entities

    def _entity_order_index(self, entity: str) -> int:
        try:
            return CANONICAL_ENTITY_ORDER.index(entity)
        except ValueError:
            return len(CANONICAL_ENTITY_ORDER) + 1

    def _build_bids_name(self, entities: OrderedDict[str, str], suffix: str) -> str:
        if not ALLOWED_SUFFIX_PATTERN.fullmatch(suffix):
            raise ValueError(f"Suffix '{suffix}' contains invalid characters")

        parts = [f"{key}-{value}" for key, value in entities.items()]
        parts.append(suffix)
        return "_".join(parts)

    def _normalize_base(self, base_name: str) -> str:
        normalized = re.sub(r"_+", "_", base_name)
        normalized = normalized.strip("_")
        return normalized

    def _validate_bids_name(self, base_name: str) -> None:
        try:
            entities, suffix = self._parse_bids_name(base_name)
        except ValueError as exc:
            raise ValueError(f"BIDS validation failed: {exc}")

        if not ALLOWED_SUFFIX_PATTERN.fullmatch(suffix):
            raise ValueError(f"Suffix '{suffix}' contains invalid characters")

        for key, value in entities.items():
            if not ALLOWED_ENTITY_VALUE_PATTERN.fullmatch(value):
                raise ValueError(f"Entity '{key}' value '{value}' contains invalid characters")

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------
    def _ensure_no_collisions(self, root: Path, planned_moves: List[Tuple[Path, Path]]) -> None:
        targets = {}
        for old_rel, new_rel in planned_moves:
            if old_rel == new_rel:
                continue
            if new_rel in targets and targets[new_rel] != old_rel:
                raise RuntimeError(f"Multiple files want to rename to {new_rel}")
            targets[new_rel] = old_rel

        for old_rel, new_rel in planned_moves:
            if old_rel == new_rel:
                continue
            target_path = root / new_rel
            if target_path.exists() and target_path != (root / old_rel):
                raise RuntimeError(f"Target {new_rel} already exists")

    def _execute_moves(self, root: Path, planned_moves: List[Tuple[Path, Path]]) -> None:
        if not planned_moves:
            self.log("No files needed renaming")
            return

        for old_rel, new_rel in planned_moves:
            if old_rel == new_rel:
                continue

            old_path = root / old_rel
            new_path = root / new_rel

            if self.dry_run:
                self.log(f"Would rename {old_rel} -> {new_rel}")
                continue

            if self.backup_enabled:
                self._backup_file(old_path)

            new_path.parent.mkdir(parents=True, exist_ok=True)
            old_path.rename(new_path)
            self.processed_files.append(str(new_rel))
            self.log(f"Renamed {old_rel} -> {new_rel}")

    def _backup_file(self, original_path: Path) -> None:
        if not self.backup_root:
            return
        relative = original_path.relative_to(self.backup_root)
        backup_path = (self.backup_root / self.backup_base_dirname / relative)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original_path, backup_path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _strip_all_suffixes(self, name: str) -> str:
        base = name
        for suffix in Path(name).suffixes:
            if suffix:
                base = base[: -len(suffix)]
        return base

    def _collect_suffix(self, name: str) -> str:
        suffixes = "".join(Path(name).suffixes)
        return suffixes


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rename BIDS files safely with entity-aware transformations"
    )

    parser.add_argument("--root", "-r", required=True,
                        help="Path to the BIDS dataset root")
    parser.add_argument("--pattern", "-p", default="*",
                        help="Glob pattern to limit files (default: *)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without touching files")
    parser.add_argument("--verbose", action="store_true",
                        help="Show detailed logging")
    parser.add_argument("--no-backup", action="store_true",
                        help="Disable copying originals to sourcedata/backup before renaming")

    # Filters similar to JSON tool
    parser.add_argument("--ses", dest="session",
                        help="Only rename files from a specific session")
    parser.add_argument("--modality", choices=["anat", "func", "dwi", "fmap", "perf", "eeg", "ieeg", "meg"],
                        help="Restrict to a particular modality folder")
    parser.add_argument("--file", dest="filename_pattern",
                        help="fnmatch-style pattern applied to filenames")

    # Transform operations
    parser.add_argument("--remove-substring", nargs="*", default=[],
                        help="Remove exact substrings from filenames before validation")
    parser.add_argument("--replace", nargs="*", default=[],
                        help="String replacements in OLD:NEW form (applied before entity ops)")
    parser.add_argument("--set-entity", nargs="*", default=[],
                        help="Set or add entity values in key=value form")
    parser.add_argument("--remove-entity", nargs="*", default=[],
                        help="Remove entire entities (e.g., acq)")

    return parser


def parse_replace_pairs(values: List[str]) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for raw in values:
        if ":" not in raw:
            raise ValueError(f"Invalid replace specification '{raw}'. Use OLD:NEW format")
        old, new = raw.split(":", 1)
        pairs.append((old, new))
    return pairs


def parse_entity_assignments(values: List[str]) -> Dict[str, str]:
    assignments: Dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"Invalid entity assignment '{raw}'. Use key=value format")
        key, value = raw.split("=", 1)
        assignments[key] = value
    return assignments


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    renamer = BIDSFileRenamer(verbose=args.verbose, dry_run=args.dry_run)
    renamer.backup_enabled = not args.no_backup

    renamer.remove_substrings = args.remove_substring or []
    renamer.replace_pairs = parse_replace_pairs(args.replace or [])
    renamer.remove_entities = args.remove_entity or []
    renamer.set_entities = parse_entity_assignments(args.set_entity or [])

    renamer.rename(
        root_path=args.root,
        pattern=args.pattern,
        session=args.session,
        modality=args.modality,
        filename_pattern=args.filename_pattern
    )

    processed = len(renamer.processed_files)
    errors = len(renamer.error_files)
    print("\nRename Summary:")
    print(f"  Files renamed: {processed}")
    print(f"  Files with errors: {errors}")
    if renamer.dry_run:
        print("  (dry-run mode: no files were changed)")


if __name__ == "__main__":
    main()
