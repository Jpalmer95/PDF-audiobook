import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import requests # Required for requests.exceptions.RequestException

# Add the parent directory (audiobook_generator) to sys.path
current_file_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_file_dir)
sys.path.insert(0, parent_dir)

from src.main import chunk_text, extract_text_from_pdf, convert_chunk_to_speech, KOKORO_API_URL

# Test instructions:
# To run these tests:
# 1. Navigate to the `audiobook_generator` directory (the main project root).
# 2. Run the tests using Python's unittest module:
#    python -m unittest discover tests
# Or, to run this specific file:
#    python -m unittest tests/test_main.py

class TestChunkingAndExtraction(unittest.TestCase): # Renamed for clarity

    def setUp(self):
        """Load sample text before each test."""
        sample_text_path = os.path.join(current_file_dir, "sample.txt")
        try:
            with open(sample_text_path, 'r') as f:
                self.sample_text = f.read()
        except FileNotFoundError:
            self.fail(f"Setup failed: sample.txt not found at {sample_text_path}. "
                      "Ensure it's in the tests directory.")

        self.longer_text = (
            "This is the first sentence. It is of a moderate length. "
            "Here is a second sentence, providing more content for our test. "
            "The third sentence aims to extend the text further, so that chunking can be properly evaluated. "
            "Let's add a fourth sentence; variety in sentence structure is also good. "
            "Finally, the fifth sentence concludes this sample paragraph, making it suitable for chunking tests with overlap."
        )

    def test_chunk_text_basic(self):
        chunks = chunk_text(self.sample_text, chunk_size=50, chunk_overlap=10)
        self.assertTrue(len(chunks) >= 1)
        if len(chunks) > 1:
            overlap_content = chunks[0][-(10+5):]
            self.assertTrue(chunks[1].startswith(chunks[0][len(chunks[0])-10:]) or chunks[1][:10] in overlap_content)
        recombined_text = ""
        if chunks:
            recombined_text = chunks[0]
            for i in range(1, len(chunks)):
                 recombined_text += chunks[i][10:]
        self.assertTrue(self.sample_text.replace("\n", " ").strip() in recombined_text.replace("\n", " ").strip()
                        or self.sample_text.strip() in recombined_text.strip())

    def test_chunk_text_longer_text_and_varying_sizes(self):
        test_cases = [
            {"text": self.longer_text, "size": 100, "overlap": 20},
            {"text": self.longer_text, "size": 70, "overlap": 10},
            {"text": self.longer_text, "size": 200, "overlap": 30},
            {"text": "Short text.", "size": 50, "overlap": 5}
        ]
        for i, tc in enumerate(test_cases):
            with self.subTest(case_num=i, size=tc["size"], overlap=tc["overlap"]):
                chunks = chunk_text(tc["text"], chunk_size=tc["size"], chunk_overlap=tc["overlap"])
                self.assertTrue(len(chunks) >= 1)
                full_reconstructed = ""
                if not chunks: continue
                full_reconstructed = chunks[0]
                for j in range(len(chunks)):
                    if j < len(chunks) -1 :
                        self.assertTrue(abs(len(chunks[j]) - tc["size"]) < max(tc["overlap"] + 20, 50))
                    if j > 0:
                        if tc["overlap"] > 0 and len(chunks[j-1]) > tc["overlap"]:
                            overlap_segment_from_prev = chunks[j-1][-tc["overlap"]:]
                            start_of_current_chunk = chunks[j][:tc["overlap"]]
                            self.assertEqual(start_of_current_chunk, overlap_segment_from_prev)
                        full_reconstructed += chunks[j][tc["overlap"]:]
                original_no_space = tc["text"].replace(" ", "").replace("\n", "")
                reconstructed_no_space = full_reconstructed.replace(" ", "").replace("\n", "")
                self.assertTrue(len(reconstructed_no_space) >= len(original_no_space) - len(chunks))

    def test_chunk_text_edge_cases(self):
        self.assertEqual(chunk_text("", chunk_size=50, chunk_overlap=10), [])
        short_text = "Tiny."
        chunks = chunk_text(short_text, chunk_size=5, chunk_overlap=1)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0], short_text)
        chunks = chunk_text(short_text, chunk_size=3, chunk_overlap=1)
        self.assertEqual(chunks, ["Tin", "ny."]) # Adjusted based on previous step's reasoning

    def test_pdf_extraction_manual_placeholder(self):
        print("\nINFO: PDF extraction functionality (extract_text_from_pdf) "
              "should be tested manually with various PDF files.")
        sample_pdf_path = os.path.join(current_file_dir, "sample.pdf")
        if os.path.exists(sample_pdf_path):
            print(f"Attempting basic check with existing '{sample_pdf_path}'...")
            extracted_text = extract_text_from_pdf(sample_pdf_path)
            self.assertIsNotNone(extracted_text)
            if extracted_text:
                 self.assertTrue(len(extracted_text) > 0)
                 self.assertTrue("page one" in extracted_text.lower())
                 self.assertTrue("page two" in extracted_text.lower())
            else:
                print("WARNING: sample.pdf exists but no text could be extracted.")
        else:
            print(f"NOTE: '{sample_pdf_path}' not found. Skipping basic PDF extraction check.")


class TestTTSConversion(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for audio output files
        self.test_output_dir_obj = tempfile.TemporaryDirectory()
        self.test_output_dir_name = self.test_output_dir_obj.name
        # print(f"Created temp dir: {self.test_output_dir_name}") # For debugging

    def tearDown(self):
        # Cleanup the temporary directory
        self.test_output_dir_obj.cleanup()
        # print(f"Cleaned up temp dir: {self.test_output_dir_name}") # For debugging

    @patch('src.main.requests.post')
    def test_convert_chunk_to_speech_success(self, mock_post):
        # Configure the mock response for successful API call
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'sample_audio_content_bytes' # Simulated MP3 audio bytes
        mock_post.return_value = mock_response

        test_text = "This is a test sentence."
        test_lang = "en"

        # Call the function under test
        audio_file_path = convert_chunk_to_speech(test_text, test_lang, self.test_output_dir_name)

        # Assertions
        self.assertIsNotNone(audio_file_path, "Audio file path should not be None on success.")
        self.assertTrue(os.path.exists(audio_file_path), "Audio file should be created.")

        # Verify the content of the created file
        with open(audio_file_path, 'rb') as f:
            file_content = f.read()
        self.assertEqual(file_content, b'sample_audio_content_bytes', "Audio file content does not match expected.")

        # Assert that requests.post was called correctly
        expected_payload = {"text": test_text, "lang": test_lang}
        mock_post.assert_called_once_with(KOKORO_API_URL, json=expected_payload, timeout=180) # KOKORO_API_URL from src.main

    @patch('src.main.requests.post')
    def test_convert_chunk_to_speech_api_error(self, mock_post):
        # Configure the mock response for an API error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        test_text = "Another test sentence."

        # Call the function
        result_path = convert_chunk_to_speech(test_text, "en", self.test_output_dir_name)

        # Assertions
        self.assertIsNone(result_path, "Should return None on API error.")
        mock_post.assert_called_once() # Check that the API was called

    @patch('src.main.requests.post')
    def test_convert_chunk_to_speech_request_exception(self, mock_post):
        # Configure mock_post to raise a RequestException
        mock_post.side_effect = requests.exceptions.RequestException("Test network error")

        test_text = "Sentence that will cause a network error."

        # Call the function
        result_path = convert_chunk_to_speech(test_text, "en", self.test_output_dir_name)

        # Assertions
        self.assertIsNone(result_path, "Should return None when a request exception occurs.")
        mock_post.assert_called_once()

    @patch('src.main.os.makedirs') # Mock os.makedirs to simulate failure
    @patch('src.main.requests.post') # Still need to mock post to avoid actual calls
    def test_convert_chunk_to_speech_os_error_creating_dir(self, mock_post, mock_makedirs):
        # Configure os.makedirs to raise an OSError
        mock_makedirs.side_effect = OSError("Test permission error creating directory")

        # This response setup for mock_post is just to ensure it's a valid mock,
        # but the function should ideally fail before calling post if makedirs fails.
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'audio_data'
        mock_post.return_value = mock_response

        test_text = "Text for directory creation failure test."

        # Call the function using a path that doesn't exist to trigger makedirs
        # Note: TemporaryDirectory in setUp usually creates the dir.
        # We need to ensure convert_chunk_to_speech tries to create 'output_path' if it doesn't exist.
        # The current implementation of convert_chunk_to_speech calls os.makedirs(output_path)
        # if not os.path.exists(output_path).
        # So, we can pass a subdirectory within our temp dir that doesn't exist yet.
        non_existent_subdir = os.path.join(self.test_output_dir_name, "new_sub_dir_for_os_error_test")

        result_path = convert_chunk_to_speech(test_text, "en", non_existent_subdir)

        self.assertIsNone(result_path, "Should return None if directory creation fails.")
        mock_makedirs.assert_called_once_with(non_existent_subdir) # Verify makedirs was called with the path
        mock_post.assert_not_called() # requests.post should not be called if dir creation fails

if __name__ == '__main__':
    unittest.main()
```
