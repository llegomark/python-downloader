# Python Parallel File Downloader

This Python script downloads a list of files concurrently, making efficient use of network bandwidth and CPU for faster downloads. It includes features for resuming interrupted downloads, error handling, retry mechanisms, progress tracking, and customizable settings.

## Features

- **Parallel Downloads:**  Downloads multiple files simultaneously using Python's `concurrent.futures` module for optimized speed.
- **Resume Support:**  Resumes partially downloaded files from where they left off, saving time and bandwidth.
- **Error Handling:** Robustly handles network errors, file system errors, and unexpected issues, providing informative log messages.
- **Retry Mechanism:**  Automatically retries failed downloads a configurable number of times.
- **Progress Bar:** Displays a progress bar using `tqdm` to visualize the download status.
- **Configuration File:** Reads settings (download folder, log file, concurrency, etc.) from a `config.ini` file.
- **Logging:**  Logs events and errors to a file for easy monitoring and debugging.
- **Customizable:** Adjust download concurrency, retry attempts, timeouts, and other parameters via the configuration file. 

## Requirements

- Python 3.12 or higher
- `tqdm` library 

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/llegomark/python-downloader.git
   cd python-downloader
   ```

2. **Install dependencies (recommended in a virtual environment):**
   ```bash
   python -m venv env 
   source env/bin/activate  # On Windows: env\Scripts\activate
   pip install -r requirements.txt
   ```

## Configuration

1. **Create `config.ini`:** Copy the `config.ini.example` file to `config.ini` and edit the values:

   ```ini
   [folders]
   downloads = C:\Users\markllego\Downloads\  ; Path to your main downloads folder

   [files]
   input = urls.txt         ; Path to your text file containing the list of URLs

   [network]
   connect_timeout = 10    ; Connect timeout for requests in seconds
   read_timeout = 30       ; Read timeout for requests in seconds

   [settings]
   max_workers = 4          ; Maximum number of parallel downloads
   retry_count = 3          ; Number of times to retry failed downloads
   retry_delay = 5         ; Delay in seconds between retry attempts
   ```

2. **Create `urls.txt`:** In the same directory as the script, create a text file named `urls.txt` and add the URLs of the files you want to download, each on a new line.

## Usage

To run the downloader:

```bash
python downloader.py config.ini -l download_log.txt
```

**Arguments:**

- `config.ini`: Path to your configuration file.
- `-l download_log.txt`: (Optional) Specifies the log file path. 

## Example

1. **config.ini:**
   ```ini
   [folders]
   downloads = C:\Users\markllego\Downloads\

   [files]
   input = urls.txt 

   [network]
   connect_timeout = 10 
   read_timeout = 30    

   [settings]
   max_workers = 8        
   retry_count = 2       
   retry_delay = 3      
   ```

2. **urls.txt:**
   ```
   https://example.com/file1.zip
   https://example.com/file2.pdf
   https://example.com/file3.jpg
   ```

3. **Run the script:**
   ```bash
   python downloader.py config.ini -l download_log.txt
   ```

## Contributing

Contributions are welcome! Feel free to open issues or pull requests.

## License

This project is licensed under the [MIT License](LICENSE).