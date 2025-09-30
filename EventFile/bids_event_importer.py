#!/usr/bin/env python3
"""BIDS Event Importer - safely copy events/physio files into an existing BIDS dataset."""

from __future__ import annotations

import argparse
import fnmatch
import gzip
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass
class ImportResult:
    copied: List[Path]
    skipped: List[Tuple[Path, str]]
    errors: List[Tuple[Path, str]]


class BIDSEventImporter:
    """Copy BIDS sidecar-like files (events/physio) into the correct dataset folders."""

    MODALITY_ORDER = [
        "func",
        "beh",
        "dwi",
        "anat",
        "meg",
        "eeg",
        "ieeg",
        "perf",
        "pet",
    ]

    def __init__(self, verbose: bool = False, dry_run: bool = False, overwrite: bool = False,
                 min_event_lines: int = 6) -> None:
        self.verbose = verbose
        self.dry_run = dry_run
        self.overwrite = overwrite
        self.min_event_lines = min_event_lines

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def import_files(
        self,
        source_dir: Path,
        bids_root: Path,
        include_events: bool,
        include_physio: bool,
        pattern: Optional[str] = None,
        session_filter: Optional[str] = None,
        subject_filter: Optional[str] = None,
    ) -> ImportResult:
        self._validate_directories(source_dir, bids_root)

        files = self._collect_source_files(
            source_dir, include_events, include_physio, pattern, session_filter, subject_filter
        )

        copied: List[Path] = []
        skipped: List[Tuple[Path, str]] = []
        errors: List[Tuple[Path, str]] = []

        if not files:
            self._log("No matching files found in source directory")
            return ImportResult(copied, skipped, errors)

        self._log(f"Found {len(files)} candidate files to import", level="INFO")

        for source_file in files:
            try:
                info = self._describe_file(source_file)
            except ValueError as exc:
                message = f"{exc}"
                errors.append((source_file, message))
                self._log(f"Skipping {source_file.name}: {message}", level="ERROR")
                continue

            if info.kind == "events" and not self._event_file_has_enough_lines(source_file):
                skipped.append((source_file, "events file too short"))
                self._log(
                    f"Skipping {source_file.name}: fewer than {self.min_event_lines} rows", level="WARNING"
                )
                continue

            try:
                target_dir = self._determine_target_dir(bids_root, info)
            except RuntimeError as exc:
                errors.append((source_file, str(exc)))
                self._log(f"Skipping {source_file.name}: {exc}", level="ERROR")
                continue

            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = target_dir / source_file.name

            if target_path.exists() and not self.overwrite:
                skipped.append((source_file, "already exists"))
                self._log(f"Skipping {source_file.name}: target already exists (use --overwrite)")
                continue

            if self.dry_run:
                copied.append(target_path)
                self._log(f"Would copy {source_file} -> {target_path}")
                continue

            if target_path.exists():
                target_path.unlink()

            shutil.copy2(source_file, target_path)
            copied.append(target_path)
            self._log(f"Copied {source_file} -> {target_path}")

            if info.kind == "physio":
                self._copy_physio_json(source_file, target_dir)

        return ImportResult(copied, skipped, errors)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _validate_directories(self, source: Path, bids_root: Path) -> None:
        if not source.exists() or not source.is_dir():
            raise FileNotFoundError(f"Source directory not found: {source}")
        if not bids_root.exists() or not bids_root.is_dir():
            raise FileNotFoundError(f"BIDS root directory not found: {bids_root}")

    def _collect_source_files(
        self,
        source: Path,
        include_events: bool,
        include_physio: bool,
        pattern: Optional[str],
        session_filter: Optional[str],
        subject_filter: Optional[str],
    ) -> List[Path]:
        candidate_files: List[Path] = []
        if include_events:
            candidate_files.extend(source.rglob("*_events.tsv"))
            candidate_files.extend(source.rglob("*_events.tsv.gz"))
        if include_physio:
            candidate_files.extend(source.rglob("*_physio.tsv"))
            candidate_files.extend(source.rglob("*_physio.tsv.gz"))

        unique_files = sorted(set(candidate_files))
        if pattern:
            unique_files = [f for f in unique_files if fnmatch.fnmatch(f.name, pattern)]

        filtered_files: List[Path] = []
        for file_path in unique_files:
            try:
                info = self._describe_file(file_path)
            except ValueError:
                continue

            if session_filter and info.entities.get("ses") not in self._session_variants(session_filter):
                continue
            if subject_filter and info.entities.get("sub") != subject_filter:
                continue

            filtered_files.append(file_path)

        return filtered_files

    def _session_variants(self, session: str) -> Iterable[Optional[str]]:
        variants = {session}
        try:
            variants.add(f"{int(session):02d}")
        except ValueError:
            pass
        return variants

    @dataclass
    class FileInfo:
        path: Path
        kind: str  # "events" or "physio"
        entities: Dict[str, str]
        base_without_suffix: str

    def _describe_file(self, path: Path) -> "BIDSEventImporter.FileInfo":
        base_name = self._strip_extensions(path.name)
        parts = [segment for segment in base_name.split("_") if segment]
        if not parts:
            raise ValueError("filename is empty")

        suffix = parts[-1]
        if suffix not in {"events", "physio"}:
            raise ValueError("not an events or physio file")

        entities: Dict[str, str] = {}
        for part in parts[:-1]:
            if "-" not in part:
                continue
            key, value = part.split("-", 1)
            if key and value:
                entities[key] = value

        if "sub" not in entities:
            raise ValueError("missing required 'sub-' entity in filename")

        base_without_suffix = "_".join(parts[:-1])
        return self.FileInfo(path=path, kind=suffix, entities=entities, base_without_suffix=base_without_suffix)

    def _strip_extensions(self, name: str) -> str:
        base = name
        for suffix in Path(name).suffixes:
            if suffix:
                base = base[: -len(suffix)]
        return base

    def _event_file_has_enough_lines(self, path: Path) -> bool:
        try:
            if path.suffix == ".gz":
                with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
                    for line_count, _ in enumerate(f, start=1):
                        if line_count >= self.min_event_lines:
                            return True
            else:
                with path.open("r", encoding="utf-8", errors="ignore") as f:
                    for line_count, _ in enumerate(f, start=1):
                        if line_count >= self.min_event_lines:
                            return True
        except OSError:
            return False
        return False

    def _determine_target_dir(self, bids_root: Path, info: "BIDSEventImporter.FileInfo") -> Path:
        sub = info.entities["sub"]
        session = info.entities.get("ses")

        relative_parts = [f"sub-{sub}"]
        if session:
            relative_parts.append(f"ses-{session}")
        base_relative = Path(*relative_parts)

        candidate_modalities = self.MODALITY_ORDER
        best_match: Optional[Path] = None
        base_without_suffix = info.base_without_suffix

        for modality in candidate_modalities:
            modality_dir = bids_root / base_relative / modality
            if not modality_dir.exists():
                continue
            if self._directory_contains_base(modality_dir, base_without_suffix):
                best_match = modality_dir
                break

        if best_match is None:
            fallback_modalities = ["func", "beh"] if info.kind == "events" else ["func"]
            for modality in fallback_modalities:
                best_match = bids_root / base_relative / modality
                if best_match.exists():
                    break
            else:
                best_match = bids_root / base_relative / fallback_modalities[0]
                self._log(
                    f"No matching data file found for {info.path.name}; using fallback directory {best_match}",
                    level="WARNING",
                )

        return best_match

    def _directory_contains_base(self, directory: Path, base_without_suffix: str) -> bool:
        if not directory.exists():
            return False
        stem = base_without_suffix
        for candidate in directory.iterdir():
            if candidate.is_file() and (candidate.name.startswith(stem + "_") or candidate.name.startswith(stem + ".")):
                return True
        return False

    def _copy_physio_json(self, physio_file: Path, target_dir: Path) -> None:
        json_source = physio_file
        if json_source.suffix == ".gz":
            json_source = json_source.with_suffix("")
        if json_source.suffix == ".tsv":
            json_source = json_source.with_suffix(".json")
        else:
            base_name = self._strip_extensions(physio_file.name)
            json_source = physio_file.parent / f"{base_name}.json"

        if not json_source.exists():
            self._log(f"No JSON sidecar found for {physio_file.name}", level="WARNING")
            return

        target_json = target_dir / json_source.name
        if target_json.exists() and not self.overwrite:
            self._log(f"Skipping JSON sidecar {target_json.name}: target already exists")
            return

        if self.dry_run:
            self._log(f"Would copy {json_source} -> {target_json}")
            return

        if target_json.exists():
            target_json.unlink()
        shutil.copy2(json_source, target_json)
        self._log(f"Copied {json_source} -> {target_json}")

    def _log(self, message: str, level: str = "INFO") -> None:
        if self.verbose or level in {"ERROR", "WARNING"}:
            prefix = "" if level == "INFO" else f"[{level}]"
            if self.dry_run and level == "INFO":
                prefix = "[DRY-RUN]"
            print(f"{prefix} {message}")


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import BIDS events/physio files into an existing dataset",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--source", "-s", required=True, help="Directory containing new events/physio files")
    parser.add_argument("--bids-root", "-b", required=True, help="Path to the BIDS dataset root")
    parser.add_argument(
        "--events",
        action="store_true",
        help="Include *_events.tsv (enabled by default if no type specified)",
    )
    parser.add_argument(
        "--physio",
        action="store_true",
        help="Include *_physio.tsv[.gz] (disabled unless requested)",
    )
    parser.add_argument("--pattern", help="Additional fnmatch filter applied to filenames")
    parser.add_argument("--ses", dest="session", help="Session filter (e.g., 1 or 01)")
    parser.add_argument("--sub", dest="subject", help="Subject filter (e.g., sub-01)")
    parser.add_argument(
        "--min-lines",
        type=int,
        default=6,
        help="Minimum number of lines required for events files",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files at target")
    parser.add_argument("--dry-run", action="store_true", help="Preview operations without copying")
    parser.add_argument("--verbose", action="store_true", help="Show detailed logging")

    return parser


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    include_events = args.events or (not args.events and not args.physio)
    include_physio = args.physio

    importer = BIDSEventImporter(
        verbose=args.verbose,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        min_event_lines=args.min_lines,
    )

    result = importer.import_files(
        source_dir=Path(args.source).resolve(),
        bids_root=Path(args.bids_root).resolve(),
        include_events=include_events,
        include_physio=include_physio,
        pattern=args.pattern,
        session_filter=args.session,
        subject_filter=args.subject,
    )

    print("\nImport Summary:")
    print(f"  Files copied: {len(result.copied)}")
    print(f"  Files skipped: {len(result.skipped)}")
    print(f"  Files with errors: {len(result.errors)}")

    if result.skipped and args.verbose:
        print("\nSkipped files:")
        for path, reason in result.skipped:
            print(f"  - {path.name}: {reason}")

    if result.errors:
        print("\nErrors:")
        for path, reason in result.errors:
            print(f"  - {path.name}: {reason}")


if __name__ == "__main__":
    main()
