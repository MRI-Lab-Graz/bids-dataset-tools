def print_header():
    header = """
▗▖  ▗▖▗▄▄▖ ▗▄▄▄▖    ▗▖    ▗▄▖ ▗▄▄▖      ▗▄▄▖▗▄▄▖  ▗▄▖ ▗▄▄▄▄▖
▐▛▚▞▜▌▐▌ ▐▌  █      ▐▌   ▐▌ ▐▌▐▌ ▐▌    ▐▌   ▐▌ ▐▌▐▌ ▐▌   ▗▞▘
▐▌  ▐▌▐▛▀▚▖  █      ▐▌   ▐▛▀▜▌▐▛▀▚▖    ▐▌▝▜▌▐▛▀▚▖▐▛▀▜▌ ▗▞▘  
▐▌  ▐▌▐▌ ▐▌▗▄█▄▖    ▐▙▄▄▖▐▌ ▐▌▐▙▄▞▘    ▝▚▄▞▘▐▌ ▐▌▐▌ ▐▌▐▙▄▄▄▖
             MRI-Lab Graz - Code Generator               
"""
    print(header)

"""
Script Name: gen_barcode.py
Description: Returns unique subject codes for a study
Author: Karl Koschutnig
Date Created: 14.11.2024
Last Modified: 18.11.2024
Version: 1.0

----------------------------------------------------------
"""
print_header()

import barcode
from barcode.writer import ImageWriter
import random
import os
import argparse

def generate_random_subject_id(prefix, existing_ids):
    """
    Generates a random subject ID with a specified prefix (3 digits) and a 6-digit random suffix,
    ensuring uniqueness among existing IDs.

    Parameters:
    prefix (int): A 3-digit integer that serves as the prefix.
    existing_ids (set): A set of already generated subject IDs to ensure uniqueness.

    Returns:
    str: The generated unique subject ID.
    """
    while True:
        random_suffix = random.randint(100000, 999999)
        subject_id = f"{prefix:03d}{random_suffix}"
        if subject_id not in existing_ids:
            existing_ids.add(subject_id)
            return subject_id

def generate_barcode(subject_id, output_file):
    """
    Generates a barcode for the given subject ID and saves it as an image.

    Parameters:
    subject_id (str): The unique identifier for the subject.
    output_file (str): The base file name (without extension) for the saved barcode image.

    Returns:
    str: The file path to the saved barcode image.
    """
    barcode_class = barcode.get_barcode_class('code128')
    barcode_instance = barcode_class(subject_id, writer=ImageWriter())
    file_path = barcode_instance.save(output_file)  # Automatically appends .png
    return file_path

def generate_barcodes_for_study(prefix, num_subjects):
    """
    Generates barcodes for a specified number of subjects with a given prefix,
    ensuring unique subject IDs.

    Parameters:
    prefix (int): The three-digit prefix for the subject IDs.
    num_subjects (int): The number of subjects for which to generate barcodes.
    """
    study_folder = f"study-{prefix:03d}"
    if not os.path.exists(study_folder):
        os.makedirs(study_folder)

    existing_ids = set()  # To ensure uniqueness
    for _ in range(num_subjects):
        subject_id = generate_random_subject_id(prefix, existing_ids)
        output_file = os.path.join(study_folder, f"subject_{subject_id}")
        file_path = generate_barcode(subject_id, output_file)
        print(f"Generated barcode for {subject_id} saved to: {file_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate unique barcodes for a study.")
    parser.add_argument("-s", "--study", type=int, required=True, help="3-digit study code prefix")
    parser.add_argument("-n", "--num_subjects", type=int, required=True, help="Number of subjects (must not exceed 999)")
    args = parser.parse_args()

    prefix = args.study
    num_subjects = args.num_subjects

    if prefix < 100 or prefix > 999:
        print("Error: Study code must be a 3-digit number.")
        return

    if num_subjects < 1 or num_subjects > 999:
        print("Error: The number of subjects must be between 1 and 999.")
        return

    generate_barcodes_for_study(prefix, num_subjects)

if __name__ == "__main__":
    main()
