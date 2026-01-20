# Tafim Downloader Pro+ (Premium Edition)

A high-performance, aggressive file downloader featuring a modern "Glass" UI, browser integration, and thread management.

## Features

- **Standalone Application**: Single-file executable integration, no Python installation needed.
- **Hidden Temp Storage**: Keeps your download folder clean by hiding temporary merge files.
- **Aggressive Downloading**: Uses up to 128 concurrent threads and a large connection pool to maximize speed.
- **Smart Resume**: Automatically resumes broken downloads.
- **File Filtering**: Only captures specific file types (ZIP, ISO, EXE, MP4, etc.) to avoid interrupting normal browsing.
- **Browser Integration**: Automatically captures downloads from Chrome/Edge via extension.
- **Clipboard Monitor**: Detects downloadable links copied to the clipboard.
- **Modern UI**: Built with CustomTkinter for a sleek, dark-themed experience.

## Installation

### Option 1: Standalone (Recommended)
1.  Download the latest release (`TafimDownloaderPro.exe`).
2.  Run it directly. No installation required.

### Option 2: Run from Source
1.  **Install Python**: Ensure you have Python 3.10 or newer installed.
2.  **Clone the Repository**:
    ```bash
    git clone https://github.com/yourusername/tafim-downloader-pro.git
    cd tafim-downloader-pro
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

### Running from Source
```bash
python main.py
```

### Browser Extension
To enable automatic download capture:
1.  Open Chrome/Edge and go to `chrome://extensions`.
2.  Enable **Developer Mode** (toggle in top right).
3.  Click **Load unpacked**.
4.  Select the `browser_extension` folder in this project.
5.  Downloads for supported file types will now be sent to Tafim Downloader.

### Thread Configuration
Use the slider in the main UI to set the number of threads (1-128).
- **32**: Recommended default.
- **64+**: Aggressive mode for high-speed connections.

## Building the Executable

To create a standalone `.exe` file:

```bash
pyinstaller --clean TafimDownloaderPro.spec
```

The output file will be in the `dist/` folder.

## Building the Installer (MSI)

To create a professional Windows Installer:

```bash
python setup.py bdist_msi
```

This will generate a `.msi` file in the `dist/` folder that installs the app to Program Files and creates shortcuts.
