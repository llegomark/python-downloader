import sys
import datetime
import random
import urllib.parse
import time
import logging
import os
from pathlib import Path
from typing import List, Tuple
from tqdm import tqdm
from configparser import ConfigParser
from concurrent.futures import ProcessPoolExecutor, as_completed
import requests
import argparse

# Logging Configuration
log_format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format,
                    handlers=[
                        # Default log file
                        logging.FileHandler('download.log'),
                        logging.StreamHandler(sys.stdout)
                    ])


def create_folder(folder_path: Path) -> None:
    """
    Create a folder if it doesn't exist.

    Args:
        folder_path (Path): The path of the folder to create.
    """
    folder_path.mkdir(parents=True, exist_ok=True)


def generate_unique_filename(filename: str, extension: str) -> str:
    """Generate a unique filename, handling potential length issues."""

    max_len = 255 - len(extension) - 1  # Account for extension and underscore

    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    random_number = random.randint(0, 9999)

    # Truncate filename if needed to accommodate timestamp and random number
    if len(filename) > max_len - len(timestamp) - len(str(random_number)) - 2:
        filename = filename[:max_len - len(timestamp) -
                            len(str(random_number)) - 2]

    unique_filename = f"{filename}_{timestamp}_{random_number}{extension}"
    return unique_filename


def set_file_modified_time(file_path: Path, timestamp: float) -> None:
    """
    Set the modified time of a file to the specified timestamp.

    Args:
        file_path (Path): The path of the file.
        timestamp (float): The timestamp to set as the modified time.
    """
    file_path.touch(exist_ok=True)
    os.utime(file_path, (os.stat(file_path).st_atime, timestamp))


def download_file(url: str, config: ConfigParser) -> Tuple[bool, str, str]:
    """Downloads a file, handling errors and resuming downloads.

    Returns:
        Tuple[bool, str, str]: Success (True/False), file path, and error message (if any).
    """

    try:
        parsed_url = urllib.parse.urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            raise ValueError(f"Invalid URL: {url}")
    except ValueError as e:
        logging.error(f"Error: {str(e)}")
        return False, "", str(e)

    encoded_url = urllib.parse.quote(url, safe=':/')
    parsed_url = urllib.parse.urlparse(encoded_url)
    stem = Path(parsed_url.path).stem
    suffix = Path(parsed_url.path).suffix

    # Determine the subfolder based on the file name prefix
    if stem.startswith('DM_'):
        subfolder = 'DM'
    elif stem.startswith('DO_'):
        subfolder = 'DO'
    elif stem.startswith('DA_'):
        subfolder = 'DA'
    else:
        subfolder = ''

    # Create the Downloads folder if it doesn't exist
    downloads_folder = Path(config.get('folders', 'downloads'))
    if not downloads_folder.is_dir():
        raise ValueError(f"Invalid downloads folder: {downloads_folder}")
    create_folder(downloads_folder)

    # Create the subfolder inside the Downloads folder if it doesn't exist
    if subfolder:
        subfolder_path = downloads_folder / subfolder
        create_folder(subfolder_path)
        output_file = subfolder_path / generate_unique_filename(stem, suffix)
    else:
        logging.warning(f"No subfolder specified for URL: {url}")
        output_file = downloads_folder / generate_unique_filename(stem, suffix)

    # Check if the file already exists with the same timestamp
    if output_file.exists():
        response = requests.head(encoded_url)
        if 'Last-Modified' in response.headers:
            remote_timestamp = time.mktime(datetime.datetime.strptime(
                response.headers['Last-Modified'], '%a, %d %b %Y %H:%M:%S %Z').timetuple())
            local_timestamp = output_file.stat().st_mtime
            if remote_timestamp == local_timestamp:
                logging.info(f"Skipping download: {
                             url} (File already exists with the same timestamp)")
                return True, str(output_file), ""

    # Check if the file exists and get the local size
    local_size = output_file.stat().st_size if output_file.exists() else 0

    # Get the remote file size
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'}
    response = requests.head(encoded_url, headers=headers)
    remote_size = int(response.headers.get('Content-Length', 0))

    if local_size >= remote_size:
        logging.info(f"Skipping download: {
                     url} (File already exists and is up to date)")
        return True, str(output_file), ""

    # Download the file with resume support
    headers = {'Range': f'bytes={local_size}-',
               'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'}
    response = requests.get(encoded_url, headers=headers, stream=True, timeout=(
        config.getint('network', 'connect_timeout'), config.getint('network', 'read_timeout')))

    if response.status_code == 206:
        with output_file.open('ab') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
    elif response.status_code == 200:
        with output_file.open('wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
    else:
        logging.error(f"Error: Download failed for '{
                      url}' with status code {response.status_code}")
        return False, str(output_file), f"Download failed with status code {response.status_code}"

    # Check if the downloaded file has the expected size
    if output_file.stat().st_size != remote_size:
        error_message = f"Downloaded file size does not match expected size for '{
            url}'"
        logging.error(f"Error: {error_message}")
        return False, str(output_file), error_message

    logging.info(f"Downloaded: {url}")

    # Get the modified time of the remote file
    if 'Last-Modified' in response.headers:
        remote_timestamp = time.mktime(datetime.datetime.strptime(
            response.headers['Last-Modified'], '%a, %d %b %Y %H:%M:%S %Z').timetuple())
        set_file_modified_time(output_file, remote_timestamp)

        # Check if the modified time of the downloaded file is set correctly
        if output_file.stat().st_mtime != remote_timestamp:
            logging.warning(
                f"Warning: Modified time of downloaded file does not match remote file for '{url}'")

    return True, str(output_file), ""


def download_files_parallel(urls: List[str], config: ConfigParser, max_workers: int) -> List[Tuple[bool, str, str]]:
    """
    Download files in parallel using a process pool executor.

    Args:
        urls (List[str]): List of URLs to download.
        config (ConfigParser): The configuration object.
        max_workers (int): Maximum number of worker processes.

    Returns:
        List[Tuple[bool, str, str]]: List of tuples containing a boolean indicating if the download was successful, 
                                    the path of the downloaded file, and an error message (if any).
    """
    if max_workers <= 0:
        raise ValueError("max_workers must be a positive integer.")

    num_urls = len(urls)
    if max_workers > num_urls:
        max_workers = num_urls
        logging.warning(f"Reduced max_workers to {
                        max_workers} to match the number of URLs.")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_file, url, config) for url in urls]
        results = [future.result() for future in tqdm(as_completed(
            futures), total=num_urls, unit='file', desc='Downloading')]
    return results


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Download files from a list of URLs in parallel.')
    parser.add_argument('config_file', type=str,
                        help='Path to the configuration file.')
    parser.add_argument('-l', '--log-file', type=str, default='download.log',
                        help='Path to the log file (default: download.log)')
    args = parser.parse_args()

    # Update logging configuration with custom log file
    for handler in logging.root.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            logging.root.removeHandler(handler)
    logging.basicConfig(level=logging.INFO, format=log_format,
                        handlers=[
                            logging.FileHandler(args.log_file),
                            logging.StreamHandler(sys.stdout)
                        ])

    # Load configuration
    config = ConfigParser()
    config.read(args.config_file)

    input_file = Path(config.get('files', 'input'))
    max_workers = config.getint('settings', 'max_workers')
    retry_count = config.getint('settings', 'retry_count')
    retry_delay = config.getint('settings', 'retry_delay')

    # Validate configuration
    if not input_file.is_file():
        raise ValueError(
            f"Input file does not exist or is not a file: {input_file}")
    if retry_count < 0:
        raise ValueError(f"Invalid retry count: {
                         retry_count}. Must be a non-negative integer.")
    if retry_delay < 0:
        raise ValueError(f"Invalid retry delay: {
                         retry_delay}. Must be a non-negative integer.")

    with input_file.open('r') as file:
        urls = file.read().splitlines()

    for attempt in range(retry_count + 1):
        results = download_files_parallel(urls, config, max_workers)
        failed_urls = [url for url, (success, _, _) in zip(
            urls, results) if not success]

        if not failed_urls:
            logging.info("All downloads completed successfully.")
            break

        urls = failed_urls
        logging.warning(f"Retry attempt {
                        attempt + 1} for {len(failed_urls)} failed URLs.")

        if attempt < retry_count:
            logging.info(f"Waiting for {
                         retry_delay} seconds before retrying...")
            time.sleep(retry_delay)
    else:
        logging.error(f"Failed to download {len(urls)} files after {
                      retry_count + 1} attempts.")
        sys.exit(1)


if __name__ == '__main__':
    main()
