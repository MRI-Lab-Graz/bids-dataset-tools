# PMU2BIDS – Convert Siemens Physio Data to BIDS

This MATLAB script converts Siemens physiological recordings (`.puls`, `.resp`) into [BIDS-compatible](https://bids.neuroimaging.io/) `physio.tsv.gz` and JSON sidecars. It aligns physiological recordings with the fMRI BOLD scan using `AcquisitionTime` and scanner triggers. It expects XA31 or XA50!

Read-in functions were taken from [PhysIO](https://github.com/ComputationalPsychiatry/PhysIO). They did an amazing job! 


## Features

- Supports `PPU` (cardiac) and `RESP` (respiratory) signals
- Reads BOLD scan timing from associated `_bold.json` files
- Writes compressed `.tsv.gz` output and BIDS-compliant `.json` metadata
- Tracks and logs results in a summary table

## Prerequisites

- MATLAB (tested with R2022b or newer)
- [JSONlab](https://github.com/fangq/jsonlab) or similar JSON support for MATLAB
- Toolboxes:
  - `tapas_physio_read_physlogfiles_siemens_raw`
  - `gpt_physio_siemens_line2table` (custom or provided with your repo)

## Usage

1. Prepare a config file in JSON format (example below).

2. Run the script in MATLAB:

   ```matlab
   config = jsondecode(fileread('config.json'));
   % Assign values manually or use helper
   puls_path = config.puls_path;
   phys_output_dir = config.phys_output_dir;
   json_bold_path = config.json_bold_path;
   nr_vols = config.nr_vols;
   PMU2bids  % main script
   ```

Example config.json

   ```json
{
 "puls_path": "/path/to/physio/ses-1/resp",
 "phys_output_dir": "/path/to/output/bids",
 "json_bold_path": "/path/to/bold/jsons",
 "nr_vols": 250
}
   ```

## Expected File Naming

Input files must follow this pattern:

```bash 
sub-<ID>_ses-<session>_task-rest_recording-<modality>_physio.<ext>
```

Where <ext> is .puls or .resp.

### Example:

```bash 
sub-1293175_ses-3_task-rest_recording-cardiac_physio.puls
sub-1293175_ses-3_task-rest_recording-respiratory_physio.resp
```

## Output

For each valid input file, the following will be generated:

- sub-..._recording-<modality>_physio.tsv.gz
- sub-..._recording-<modality>_physio.json

A summary text file like:

Sum_up_conversion_2025-04-08_14_23_57.txt

## License

MIT License

## Author

Karl Koschutnig
MRI-Lab Graz
