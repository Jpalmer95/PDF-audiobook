# Audiobook Generator

Audiobook Generator is a Python-based command-line tool that converts PDF books into audiobooks. It extracts text from PDF files, splits it into manageable chunks, then utilizes a locally running instance of the **Kokoro-FastAPI** for text-to-speech conversion, and finally merges these audio chunks into a single MP3 audio file.

## Features

*   Extracts text content from PDF files.
*   Chunks text into manageable sizes for efficient Text-to-Speech (TTS) processing.
*   Converts text chunks to speech (MP3 format) using a locally running **Kokoro-FastAPI** instance.
*   Merges individual audio chunks into a single, coherent audiobook file.
*   Provides a command-line interface (CLI) for easy operation and customization.
*   Allows customization of output filename, language, chunk size, and temporary file handling.

## Prerequisites

### For Audiobook Generator:
*   Python 3.7 or higher.
*   `pip` (Python package installer), which usually comes with Python.
*   (Potentially) `ffmpeg` for audio processing with `pydub` (see Troubleshooting).

### For Kokoro-FastAPI (Text-to-Speech Engine):
*   **Git**: For cloning the Kokoro-FastAPI repository.
*   **Python Environment for Kokoro-FastAPI**: It's recommended to set up Kokoro-FastAPI in its own Python environment.
*   **`astral-uv`**: A Python package required by Kokoro-FastAPI. Install via pip: `pip install astral-uv`.
*   **`espeak-ng`**: A system-level speech synthesizer, often used as a fallback or component by TTS systems. Installation varies by OS (e.g., `sudo apt-get install espeak-ng` on Debian/Ubuntu).
*   **NVIDIA GPU with CUDA Drivers**: For GPU-accelerated TTS performance with Kokoro-FastAPI. CPU mode is available but significantly slower.
*   Refer to the Kokoro-FastAPI documentation for its complete and up-to-date prerequisites.

## Setup and Installation

### 1. Audiobook Generator Setup

1.  **Clone this repository** (if you obtained it as a Git repository) or download the source files into a directory on your computer.
    ```bash
    # Example if cloning:
    # git clone <audiobook_generator_repository_url>
    # cd audiobook_generator
    ```

2.  **Navigate to the `audiobook_generator` directory** (if you are not already there).
    ```bash
    cd path/to/audiobook_generator
    ```

3.  **Create a virtual environment** for the audiobook generator:
    ```bash
    python -m venv venv
    ```

4.  **Activate the virtual environment**:
    *   On Windows:
        ```bash
        venv\Scripts\activate
        ```
    *   On macOS and Linux:
        ```bash
        source venv/bin/activate
        ```
    You should see `(venv)` at the beginning of your command prompt.

5.  **Install the required Python dependencies** for the audiobook generator:
    ```bash
    pip install -r requirements.txt
    ```
    (The `requirements.txt` for this project includes `PyPDF2`, `pydub`, and `requests`.)

### 2. Setting up Kokoro-FastAPI (Required for Text-to-Speech)

The audiobook generator now uses Kokoro-FastAPI for text-to-speech conversion. You need to set it up and run it locally. It's recommended to install and run Kokoro-FastAPI in a **separate terminal and environment** from the Audiobook Generator.

1.  **Clone the Kokoro-FastAPI repository:**
    ```bash
    git clone https://github.com/remsky/Kokoro-FastAPI.git
    cd Kokoro-FastAPI
    ```

2.  **Install Kokoro-FastAPI Prerequisites & Dependencies:**
    *   Ensure you have `astral-uv` installed (e.g., `pip install astral-uv` - this could be global or in Kokoro's own virtual environment).
    *   Ensure `espeak-ng` is installed on your system.
    *   It is highly recommended to create a separate Python virtual environment for Kokoro-FastAPI and install its Python dependencies from its `requirements.txt` file (if provided) or setup instructions. Refer to the Kokoro-FastAPI repository for its specific Python dependency setup.

3.  **Download Models:**
    *   Run the model download script provided within the `Kokoro-FastAPI` repository (e.g., a script like `download_models.sh` or `download_models.ps1` if it exists). Follow the instructions in the Kokoro-FastAPI documentation.

4.  **Start the Kokoro-FastAPI Server:**
    *   Navigate to the `Kokoro-FastAPI` directory in your terminal.
    *   **For Windows with NVIDIA GPU:**
        ```bash
        .\start-gpu.ps1
        ```
    *   **For Linux with NVIDIA GPU:**
        ```bash
        ./start-gpu.sh
        ```
    *   **For CPU (slower):** Use `start-cpu.ps1` (Windows) or `start-cpu.sh` (Linux).
    *   Ensure this server is running (typically on `http://127.0.0.1:8000`) before you use the audiobook generator. The server console will usually indicate if it has started successfully.

## Usage

**Important**: Ensure the Kokoro-FastAPI server is running locally before executing the audiobook generator script.

The audiobook generator script is executed from the command line. Make sure your virtual environment for the *audiobook generator* is activated.

```bash
python src/main.py [ARGUMENTS]
```

The default TTS API URL used by this script is `http://127.0.0.1:8000/tts`. If your Kokoro-FastAPI server is running on a different URL or port, you can set the `KOKORO_API_URL` environment variable:
*   Windows: `set KOKORO_API_URL=http://your_host:your_port/tts`
*   macOS/Linux: `export KOKORO_API_URL=http://your_host:your_port/tts`

Below are the available command-line arguments for `src/main.py`:

| Argument              | Short | Description                                                        | Default               | Required |
|-----------------------|-------|--------------------------------------------------------------------|-----------------------|----------|
| `--pdf_file PATH`     | `-p`  | Path to the input PDF file.                                        |                       | Yes      |
| `--output_file NAME`  | `-o`  | Name for the output audiobook file.                                | `audiobook.mp3`       | No       |
| `--output_dir DIR`    | `-d`  | Directory to save the final audiobook.                             | `.` (current dir)     | No       |
| `--language LANG`     | `-l`  | Language for Text-to-Speech (e.g., 'en', 'ja'). Passed to Kokoro-FastAPI. | `en`                  | No       |
| `--chunk_size SIZE`   | `-c`  | Target character size for text chunks before TTS.                  | `2000`                | No       |
| `--temp_audio_dir DIR`| `-t`  | Directory for storing temporary audio chunk files.                 | `temp_audio_chunks`   | No       |
| `--keep_temp_files`   |       | Flag to keep temporary audio files after generation.               | Not set (False)       | No       |


## Example Usage

Here's an example of how to convert a PDF named `my_book.pdf` into an audiobook named `my_novel.mp3`, saving it in a directory called `my_audiobooks`, using English as the language (assuming Kokoro-FastAPI is running):

```bash
python src/main.py --pdf_file "path/to/your/my_book.pdf" --output_file "my_novel.mp3" --output_dir "my_audiobooks" --language "en"
```

If `my_audiobooks` directory does not exist, the script will attempt to create it.

## Troubleshooting/Notes

*   **ffmpeg for pydub**: `pydub` uses `ffmpeg` (or `libav`) for handling MP3 and other audio formats. If you encounter errors during the audio merging or export stage, you may need to install `ffmpeg` and ensure it's added to your system's PATH.
*   **PDF Text Extraction Quality**: The accuracy of text extraction heavily depends on the source PDF. Scanned PDFs (images of text) will not work without prior OCR.
*   **Kokoro-FastAPI Issues**: If experiencing issues with TTS:
    *   Ensure the Kokoro-FastAPI server is running correctly. Check its console output for any errors.
    *   Verify it's accessible at the configured URL (default `http://127.0.0.1:8000/tts`, or as set by `KOKORO_API_URL`).
    *   Check if the models for Kokoro-FastAPI were downloaded and loaded correctly.
    *   Ensure your system meets Kokoro-FastAPI's prerequisites (GPU, drivers, `espeak-ng`, `astral-uv`).
*   **Language Codes**: The `--language` parameter is passed to Kokoro-FastAPI. Refer to its documentation for supported language codes (e.g., 'en', 'ja', 'es').

## Future Enhancements (Optional)

*   Support for more output audio formats.
*   Intelligent chapter detection.
*   GUI for users not comfortable with CLI.
*   More sophisticated text cleaning.
```
