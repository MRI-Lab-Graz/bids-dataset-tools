# bids-dataset-tools

Welcome to the MRI-Lab Graz BIDS toolkit!

- **Organization:** MRI-Lab Graz
- **Contact:** [karl.koschutnig@uni-graz.at](mailto:karl.koschutnig@uni-graz.at)
- **GitHub:** [github.com/MRI-Lab-Graz/bids-dataset-tools](https://github.com/MRI-Lab-Graz/bids-dataset-tools)

Tools to modify an existing BIDS dataset.

## Available Utilities

- `json_manager/bids_json_tool.sh` – manage JSON sidecar tags with filters, dry-run, backups, templates, stats, and compliance checks.
- `json_manager/bids_rename_tool.sh` – entity-aware renaming for BIDS filenames that keeps data/sidecars synchronized and backs up originals.
- `EventFile/bids_event_tool.sh` – copy new `_events.tsv` / `_physio.tsv[.gz]` files into the correct BIDS folders with dry-run previews and smart directory detection.

See `json_manager/README.md` for detailed instructions, examples, and safety tips.
