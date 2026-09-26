import sys
import json
import struct
import requests
import logging

# Configure logging
logging.basicConfig(
    filename='verifier.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)



def read_browser_message():
    """
    Read a message from the browser extension via stdin.
    The message is prefixed with a 4-byte length header.
    """
    raw_length = sys.stdin.buffer.read(4)
    if len(raw_length) == 0:
        logging.info("No more messages from the browser extension. Exiting.")
        sys.exit(0)

    message_length = struct.unpack('=I', raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode('utf-8')
    return json.loads(message)

def send_browser_message(message):
    """
    Send a message to the browser extension via stdout.
    The message is prefixed with a 4-byte length header.
    """
    encoded_message = json.dumps(message).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('=I', len(encoded_message)))
    sys.stdout.buffer.write(encoded_message)
    sys.stdout.buffer.flush()

def find_checksum_url_via_ai(download_url: str, filename: str) -> str:
    """
    Attempt to find the checksum URL for the given ISO file using AI-based heuristics.
    """

    logging.info(f"Attempting to find checksum URL for '{filename}' at '{download_url}' using AI heuristics.")

    # API keys and endpoints for AI services would be configured here. For this example, we will simulate the AI-based approach.
    api_key = "YOUR_AI_API_KEY"  # Replace with your actual AI API key
    api_url = "https://api.example.com/find-checksum"  # Replace with the actual AI API endpoint

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Construct a higly detailed prompt for the AI model
    prompt = (
        f"You are a network parsing utility. Given this direct ISO download URL:\n"
        f"'{download_url}'\n"
        f"And this target filename:\n"
        f"'{filename}'\n"
        f"Predict the absolute URL of the companion checksum manifest file (e.g., SHA256SUMS, CHECKSUMS, or filename.sha256).\n"
        f"Return ONLY the raw absolute URL string. No markdown, no explanations."
    )

    # Construct the payload for the AI request
    payload = {
        "model": "gpt-4",  # Specify the AI model to use
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100,
        "temperature": 0.0  # Use deterministic output
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()  # Raise an error for bad responses
        predicted_url = response.json().get("predicted_url")

        # Strip code fences if the model includes them in the response
        predicted_url = predicted_url.replace("```", "").strip()

        logging.info(f"AI predicted checksum URL: {predicted_url}")

        # Verify the AI-predicted URL by sending a HEAD request to check if it exists
        verify_resp = requests.head(predicted_url, allow_redirects=True, timeout=5)
        if verify_resp.status_code == 200:
            logging.info(f"Verified checksum URL exists: {predicted_url}")
            return predicted_url

    except Exception as e:
        logging.error(f"Error during AI-based checksum URL prediction: {e}")

    # Fallback to your original heuristic method if AI prediction fails
    logging.warning("AI prediction failed or URL not valid. Falling back to heuristic method.")
    base_url = download_url.rsplit('/', 1)[0]  # Get the base URL by removing the filename
    for fallback_name in [
        f"{filename}.sha256",
        "SHA256SUMS",
        "CHECKSUMS"
    ]:
        test_url = f"{base_url}/{fallback_name}"
        try:
            if requests.head(test_url, allow_redirects=True, timeout=5).status_code == 200:
                logging.info(f"Found checksum file via heuristic: {test_url}")
                return test_url
        except requests.RequestException as e:
            logging.warning(f"Error checking {test_url}: {e}")
            continue

    raise ValueError("Could not find a valid checksum file for the given ISO using AI or heuristic methods.")

def get_remote_expected_hash(checksum_url: str, iso_filename: str) -> str:
    """
    Fetch the official checksum manifest and extract the expected hash value for the specified ISO file.
    """

    try:
        response = requests.get(checksum_url, timeout=10)
        response.raise_for_status()  # Raise an error for bad responses

        for line in response.text.splitlines():
            if iso_filename in line:
                # Extract the hash (the first item in the line)
                expected_hash = line.split()[0]
                logging.info(f"Expected hash for '{iso_filename}': {expected_hash}")
                return expected_hash
    except Exception as e:
        logging.error(f"Error fetching or parsing checksum manifest: {e}")
        return ""
    return ""  # Return an empty string if the hash is not found or an error occurs

def main():

    logging.info("Verifier started. Waiting for messages from the browser extension.")

    while True:
        try:
            message = read_browser_message()
            download_url = message.get("download_url")
            iso_filename = message.get("iso_filename")

            if not download_url or not iso_filename:
                logging.warning("Missing 'download_url' or 'iso_filename' in the message.")
                send_browser_message({"error": "Missing 'download_url' or 'iso_filename' in the message."})
                continue

            try:
                # Use AI-based method to find the checksum URL
                checksum_url = find_checksum_url_via_ai(download_url, iso_filename)
                expected_hash = get_remote_expected_hash(checksum_url, iso_filename)

                if expected_hash:
                    send_browser_message({"expected_hash": expected_hash})
                else:
                    send_browser_message({"error": f"Could not retrieve expected hash for '{iso_filename}'."})
            except ValueError as ve:
                send_browser_message({"error": str(ve)})
        except Exception as e:
            logging.critical(f"An unexpected error occurred: {e}")
            send_browser_message({"error": f"An unexpected error occurred: {str(e)}"})


if __name__ == "__main__":
    main()