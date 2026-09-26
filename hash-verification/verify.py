# An application designed to check the integrity of ISO files by verifying their hash values before installation.

import requests

def get_remote_expected_hash(checksum_url: str, iso_filename: str) -> str:
    """
    First, download the official checksum manifest and extract the expected hash value for the specified ISO file.
    """

    print(f"Fetching official manifest from: {checksum_url}")
    response = requests.get(checksum_url)
    response.raise_for_status()  # Raise an error for bad responses

    # Manifest is expected to be a text file with lines in the format: "<hash> <filename>"
    manifest_text = response.text

    for line in manifest_text.splitlines():
        if iso_filename in line:
            # Extract the hash (the first item in the line)
            expected_hash = line.split()[0]
            print(f"Expected hash for '{iso_filename}':\n {expected_hash}")
            return expected_hash

    raise ValueError(f"ISO filename '{iso_filename}' not found in the manifest.")