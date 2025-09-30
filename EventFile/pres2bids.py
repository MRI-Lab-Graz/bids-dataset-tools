# suprt dcript
import argparse
import csv
import os
import sys
import subprocess

REQUIRED_PACKAGES = ["argparse", "csv"]

def check_and_install_packages():
    missing_packages = []
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"The following required packages are missing: {', '.join(missing_packages)}")
        install = input("Do you want to install them now? (yes/no): ").strip().lower()
        if install == 'yes':
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
                print("Packages installed successfully.")
            except subprocess.CalledProcessError:
                print("Failed to install packages. Please install them manually.")
                sys.exit(1)
        else:
            print("Please install the required packages and try again.")
            sys.exit(1)

def process_log_file(log_file_path, events_output_path, summary_output_path, start_event_code, search_strings):
    # Event Table header indices based on provided log file
    ET_EVENT_TYPE = 2
    ET_CODE = 3
    ET_TIME = 4
    ET_DURATION = 7

    # Read log file into list of lists.
    log = []
    with open(log_file_path, 'r') as log_file:
        reader = csv.reader(log_file, delimiter='\t')
        for line in reader:
            log.append(line)

    # Extract scenario name and log file creation time
    scenario_name = log[0][0].split('Scenario - ')[1] if 'Scenario - ' in log[0][0] else 'Unknown'
    log_file_time = log[1][0].split('Logfile written - ')[1] if 'Logfile written - ' in log[1][0] else 'Unknown'

    # Extract subject ID from the first non-header row
    subject_id = 'Unknown'
    for row in log:
        if len(row) > 1 and row[0] != 'Subject':
            subject_id = row[0]
            break

    # Initialize event counts
    pulse_count = 0
    trial_type_counts = {search_string: 0 for search_string in search_strings}

    # Process the log and collect events.
    events = []
    log_it = iter(log)
    for l in log_it:
        if len(l) > 0 and l[0].startswith("Subject"):
            # Skip the header
            continue
        if len(l) > 1:
            events.append(l)

    # Find the first Pulse event to set the start time
    start_time = 0
    for e in events:
        if e[ET_EVENT_TYPE] == 'Pulse':
            start_time = int(e[ET_TIME])
            break

    # Adjust times relative to the start time and convert to seconds
    for e in events:
        e[ET_TIME] = (int(e[ET_TIME]) - start_time) / 10000

    # Filter events to only include "Picture" and "Response" event types and specified search strings
    filtered_events = []
    for e in events:
        if e[ET_EVENT_TYPE] == 'Pulse':
            pulse_count += 1
        elif e[ET_EVENT_TYPE] in ["Picture", "Response"]:
            for search_string in search_strings:
                if search_string in e[ET_CODE]:
                    trial_type = search_string
                    item_description = e[ET_CODE].replace(search_string, '').replace('__', '').strip('_')
                    e.append(trial_type)
                    e.append(item_description)
                    filtered_events.append(e)
                    trial_type_counts[search_string] += 1
                    break

    # Events file header
    events_header = ['onset', 'duration', 'trial_type', 'item_description']

    # Write the output events file.
    with open(events_output_path, 'w') as events_file:
        events_writer = csv.writer(events_file, delimiter='\t')
        events_writer.writerow(events_header)
        for e in filtered_events:
            onset = round(e[ET_TIME], 3)
            duration = round(int(e[ET_DURATION]) / 10000, 3) if e[ET_EVENT_TYPE] == 'Picture' else 0.000
            trial_type = e[-2]
            item_description = e[-1]
            events_writer.writerow([onset, duration, trial_type, item_description])

    # Write the summary log file
    with open(summary_output_path, 'a') as summary_file:
        summary_writer = csv.writer(summary_file, delimiter='\t')
        summary_row = [
            scenario_name,
            log_file_time,
            subject_id,
            pulse_count
        ]
        summary_row.extend(trial_type_counts[search_string] for search_string in search_strings)
        summary_writer.writerow(summary_row)

def main():
    check_and_install_packages()

    parser = argparse.ArgumentParser(
        description="Converts log files of Presentation by Neurobehavioral Systems to BIDS events files.")
    parser.add_argument(
        dest="log_dir_path",
        metavar="LOG_DIR_PATH",
        help="Path to directory containing log files."
    )
    parser.add_argument(
        dest="events_output_dir",
        metavar="EVENTS_OUTPUT_DIR",
        help="Path to directory to save output BIDS events files."
    )
    parser.add_argument(
        dest="summary_output_path",
        metavar="SUMMARY_OUTPUT_PATH",
        help="Path to save the summary log file."
    )
    parser.add_argument(
        '--start-event-code',
        dest="START_EVENT_CODE",
        default="Beginn",
        metavar="START_EVENT_CODE",
        help="Event code that marks the task start after syncing with the scanner; default is `Beginn`."
    )
    parser.add_argument(
        '--search-strings',
        dest="SEARCH_STRINGS",
        default="Fixation,Rest,Response",
        metavar="SEARCH_STRINGS",
        help="Comma-separated list of strings to search for within the code column."
    )
    args = parser.parse_args()

    if not os.path.exists(args.events_output_dir):
        os.makedirs(args.events_output_dir)

    search_strings = args.SEARCH_STRINGS.split(',')

    # Write the header of the summary log file
    with open(args.summary_output_path, 'w') as summary_file:
        summary_writer = csv.writer(summary_file, delimiter='\t')
        summary_header = [
            'scenario_name',
            'log_file_time',
            'subject_id',
            'pulse_count'
        ]
        summary_header.extend(search_strings)
        summary_writer.writerow(summary_header)

    for filename in os.listdir(args.log_dir_path):
        if filename.endswith(".log"):
            log_file_path = os.path.join(args.log_dir_path, filename)
            events_output_path = os.path.join(args.events_output_dir, f"{os.path.splitext(filename)[0]}_events.tsv")
            print(f"Processing file: {log_file_path}")
            process_log_file(log_file_path, events_output_path, args.summary_output_path, args.START_EVENT_CODE, search_strings)

if __name__ == "__main__":
    main()
