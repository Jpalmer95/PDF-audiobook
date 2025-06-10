import PyPDF2
import re
import os
import uuid
# from gtts import gTTS # Removed gTTS
import requests # Added requests
from pydub import AudioSegment
import argparse

# Define Kokoro-FastAPI endpoint URL as a global constant or configurable parameter
KOKORO_API_URL = os.getenv("KOKORO_API_URL", "http://127.0.0.1:8000/tts")

def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Audiobook Generator from PDF")
    parser.add_argument(
        "-p", "--pdf_file",
        type=str,
        required=True,
        help="Path to the input PDF file."
    )
    parser.add_argument(
        "-o", "--output_file",
        type=str,
        default="audiobook.mp3",
        help="Name for the output audiobook file (default: audiobook.mp3)."
    )
    parser.add_argument(
        "-l", "--language",
        type=str,
        default="en",
        help="Language for Text-to-Speech (e.g., 'en', 'ja'). Default: 'en'. This is passed to the TTS API."
    )
    parser.add_argument(
        "-c", "--chunk_size",
        type=int,
        default=2000,
        help="Target characters per audio chunk (default: 2000)."
    )
    parser.add_argument(
        "-t", "--temp_audio_dir",
        type=str,
        default="temp_audio_chunks",
        help="Directory for temporary audio chunks (default: temp_audio_chunks)."
    )
    parser.add_argument(
        "-d", "--output_dir",
        type=str,
        default=".",
        help="Directory to save the final audiobook (default: current directory '.')."
    )
    parser.add_argument(
        "--keep_temp_files",
        action='store_true',
        help="Keep temporary audio chunk files after merging."
    )
    return parser.parse_args()

def extract_text_from_pdf(pdf_path):
    """
    Extracts text content from a PDF file.
    Args: pdf_path: The path to the PDF file.
    Returns: The extracted text as a string, or None if an error occurs.
    """
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            full_text = []
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    full_text.append(page_text)
            return "".join(full_text) if full_text else ""
    except FileNotFoundError:
        print(f"Error: PDF file not found at {pdf_path}")
        return None
    except Exception as e:
        print(f"An error occurred during PDF processing: {e}")
        return None

def chunk_text(text: str, chunk_size: int = 2000, chunk_overlap: int = 200) -> list[str]:
    """
    Splits text into chunks. Default overlap is 10% of default chunk_size.
    """
    if not text: return []
    chunks = []
    start_index = 0
    text_len = len(text)
    while start_index < text_len:
        end_index = start_index + chunk_size
        if end_index >= text_len:
            chunks.append(text[start_index:])
            break
        actual_break_pos = -1
        search_window_start = max(start_index + chunk_size - chunk_overlap - (chunk_size // 4), start_index)
        period_break = text.rfind('.', search_window_start, end_index + 1)
        newline_break = text.rfind('\n', search_window_start, end_index + 1)
        if period_break != -1: actual_break_pos = period_break + 1
        if newline_break != -1 and newline_break + 1 > actual_break_pos:
            actual_break_pos = newline_break + 1
        chunk_end_point = actual_break_pos if (actual_break_pos != -1 and actual_break_pos > start_index) else min(end_index, text_len)
        chunks.append(text[start_index:chunk_end_point])
        next_start_index = chunk_end_point - chunk_overlap
        if next_start_index <= start_index and chunk_end_point < text_len:
            next_start_index = chunk_end_point
        start_index = next_start_index
        if start_index >= text_len: break
    return [c for c in chunks if c]

def convert_chunk_to_speech(text_chunk: str, lang: str = 'en', output_path: str = 'temp_audio') -> str | None:
    """
    Converts a text chunk to speech using Kokoro-FastAPI and saves it as an MP3 file.
    """
    if not text_chunk.strip():
        print("Warning: Empty text chunk provided for TTS.")
        return None

    if not os.path.exists(output_path):
        try:
            os.makedirs(output_path)
        except OSError as e:
            print(f"Error creating output directory {output_path}: {e}")
            return None

    payload = {"text": text_chunk, "lang": lang}

    try:
        print(f"Sending TTS request to {KOKORO_API_URL} for chunk: '{text_chunk[:50]}...' (lang: {lang})")
        response = requests.post(KOKORO_API_URL, json=payload, timeout=180) # Increased timeout

        if response.status_code == 200:
            unique_filename = f"chunk_{uuid.uuid4()}.mp3" # Assuming MP3 output from API
            audio_file_path = os.path.join(output_path, unique_filename)

            with open(audio_file_path, 'wb') as f:
                f.write(response.content)
            print(f"Successfully saved audio chunk: {audio_file_path}")
            return audio_file_path
        else:
            print(f"Error from TTS API: Status {response.status_code} - {response.text}")
            return None

    except requests.exceptions.Timeout:
        print(f"TTS request timed out after 180 seconds for chunk: '{text_chunk[:30]}...'")
        return None
    except requests.exceptions.RequestException as e:
        print(f"TTS request error for chunk '{text_chunk[:30]}...': {e}")
        return None
    except OSError as e: # Catch potential errors during file saving (e.g. disk full)
        print(f"File system error when saving audio chunk: {e}")
        return None
    except Exception as e: # Catch-all for any other unexpected errors
        print(f"An unexpected error occurred during TTS conversion: {e}")
        return None


def merge_audio_files(audio_file_paths: list[str], output_filename: str, export_format: str = "mp3") -> str | None:
    """Merges multiple audio files into a single file."""
    if not audio_file_paths:
        print("Warning: No audio files to merge.")
        return None
    combined_audio = None
    try:
        final_output_dir = os.path.dirname(output_filename)
        if final_output_dir and not os.path.exists(final_output_dir):
            os.makedirs(final_output_dir)
            print(f"Created output directory for final audiobook: {final_output_dir}")

        for i, audio_file_path in enumerate(audio_file_paths):
            if not os.path.exists(audio_file_path):
                print(f"Error: Audio file {audio_file_path} not found. Skipping.")
                continue
            try:
                segment = AudioSegment.from_file(audio_file_path)
                if combined_audio is None:
                    combined_audio = segment
                else:
                    combined_audio += segment
            except Exception as e:
                print(f"Error loading audio segment {audio_file_path}: {e}. Skipping.")
                continue

        if combined_audio is None:
             print("Error: No valid audio segments to combine.")
             return None

        combined_audio.export(output_filename, format=export_format)
        print(f"Successfully merged {len(audio_file_paths)} (valid) audio files into: {output_filename}")
        return output_filename
    except Exception as e:
        print(f"Audio merging error: {e}")
        return None

def main():
    args = parse_arguments()
    final_audiobook_path = os.path.join(args.output_dir, args.output_file)

    print(f"\n--- Starting Audiobook Generation ---")
    print(f"PDF File: {args.pdf_file}")
    print(f"Output Audiobook: {final_audiobook_path}")
    print(f"Language: {args.language}")
    print(f"Chunk Size: {args.chunk_size} chars")
    print(f"Temporary Audio Directory: {args.temp_audio_dir}")
    print(f"TTS API Endpoint: {KOKORO_API_URL}")


    print(f"\n[Step 1] Extracting text from '{args.pdf_file}'...")
    text_content = extract_text_from_pdf(args.pdf_file)
    if not text_content:
        print(f"Failed to extract text from '{args.pdf_file}' or PDF is empty. Exiting.")
        return
    print(f"Text extraction complete. Total characters: {len(text_content)}")

    overlap = int(args.chunk_size * 0.10)
    print(f"\n[Step 2] Chunking text (size: {args.chunk_size}, overlap: {overlap})...")
    chunks = chunk_text(text_content, chunk_size=args.chunk_size, chunk_overlap=overlap)
    if not chunks:
        print("Failed to generate text chunks. Exiting.")
        return
    print(f"Text chunked into {len(chunks)} parts.")

    print("\n[Step 3] Converting text chunks to speech...")
    individual_audio_files = []

    if not args.keep_temp_files and os.path.exists(args.temp_audio_dir):
        print(f"Cleaning up old files in temporary directory: {args.temp_audio_dir}")
        for f_name in os.listdir(args.temp_audio_dir):
            f_path_full = os.path.join(args.temp_audio_dir, f_name)
            try:
                os.remove(f_path_full)
            except OSError as e:
                print(f"Error deleting old temp file {f_path_full}: {e.strerror}")

    # Ensure temp_audio_dir exists *before* calling convert_chunk_to_speech in loop
    if not os.path.exists(args.temp_audio_dir):
        try:
            os.makedirs(args.temp_audio_dir)
        except OSError as e:
            print(f"Fatal: Could not create temporary directory {args.temp_audio_dir}: {e}. Exiting.")
            return


    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}...")
        audio_file = convert_chunk_to_speech(chunk, lang=args.language, output_path=args.temp_audio_dir)
        if audio_file:
            individual_audio_files.append(audio_file)
        else:
            print(f"Failed to convert chunk {i+1} to speech. Skipping this chunk.")

    if not individual_audio_files:
        print("No audio files were successfully generated. Cannot proceed to merge. Exiting.")
        return
    print(f"Successfully generated {len(individual_audio_files)} audio chunks in '{args.temp_audio_dir}'.")

    print("\n[Step 4] Merging audio files...")
    merged_audio_file = merge_audio_files(individual_audio_files, final_audiobook_path)

    if merged_audio_file:
        print(f"\n--- Audiobook Generation Complete ---")
        print(f"Final audiobook saved as: {merged_audio_file}")

        if not args.keep_temp_files:
            print("\n[Step 5] Cleaning up temporary audio chunk files...")
            cleaned_count = 0
            for f_path in individual_audio_files:
                try:
                    if os.path.exists(f_path): # Check if file still exists before trying to remove
                        os.remove(f_path)
                        cleaned_count +=1
                except OSError as e:
                    print(f"Error deleting temp file {f_path}: {e.strerror}")
            print(f"Attempted to clean {cleaned_count} temporary audio files.")
            try:
                if os.path.exists(args.temp_audio_dir) and not os.listdir(args.temp_audio_dir):
                    os.rmdir(args.temp_audio_dir)
                    print(f"Removed empty temporary directory: {args.temp_audio_dir}")
            except OSError as e:
                print(f"Error removing temporary directory {args.temp_audio_dir}: {e.strerror}")
            print("Cleanup process complete.")
        else:
            print(f"\nTemporary audio files kept in: {args.temp_audio_dir}")

    else:
        print("\n--- Audiobook Generation Failed ---")
        print("Failed to merge audio files.")

if __name__ == '__main__':
    main()
