import unittest
import json
import os
import tempfile
import base64
from unittest.mock import patch, MagicMock, mock_open
import sys

# Add the root directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import rp_handler


class TestTTSRequest(unittest.TestCase):
    """Test TTSRequest model validation."""

    def test_valid_request(self):
        request = rp_handler.TTSRequest(
            text="Hello world",
            reference_audio="base64data",
            temperature=0.8,
            speed=1.0,
            seed=42
        )
        self.assertEqual(request.text, "Hello world")
        self.assertEqual(request.reference_audio, "base64data")
        self.assertEqual(request.temperature, 0.8)
        self.assertEqual(request.speed, 1.0)
        self.assertEqual(request.seed, 42)

    def test_minimal_request(self):
        request = rp_handler.TTSRequest(text="Hello")
        self.assertEqual(request.text, "Hello")
        self.assertIsNone(request.reference_audio)
        self.assertEqual(request.temperature, 0.8)
        self.assertEqual(request.speed, 1.0)
        self.assertEqual(request.seed, 42)

    def test_text_validation(self):
        # Valid text
        rp_handler.TTSRequest(text="A")

        # Empty text should fail
        with self.assertRaises(ValueError):
            rp_handler.TTSRequest(text="")

        # Text too long should fail
        with self.assertRaises(ValueError):
            rp_handler.TTSRequest(text="A" * 1001)

    def test_temperature_validation(self):
        # Valid temperatures
        rp_handler.TTSRequest(text="Hello", temperature=0.0)
        rp_handler.TTSRequest(text="Hello", temperature=2.0)

        # Invalid temperatures
        with self.assertRaises(ValueError):
            rp_handler.TTSRequest(text="Hello", temperature=-0.1)
        with self.assertRaises(ValueError):
            rp_handler.TTSRequest(text="Hello", temperature=2.1)

    def test_speed_validation(self):
        # Valid speeds
        rp_handler.TTSRequest(text="Hello", speed=0.5)
        rp_handler.TTSRequest(text="Hello", speed=2.0)

        # Invalid speeds
        with self.assertRaises(ValueError):
            rp_handler.TTSRequest(text="Hello", speed=0.4)
        with self.assertRaises(ValueError):
            rp_handler.TTSRequest(text="Hello", speed=2.1)

    def test_seed_validation(self):
        # Valid seeds
        rp_handler.TTSRequest(text="Hello", seed=0)
        rp_handler.TTSRequest(text="Hello", seed=1000000)

        # Invalid seeds
        with self.assertRaises(ValueError):
            rp_handler.TTSRequest(text="Hello", seed=-1)
        with self.assertRaises(ValueError):
            rp_handler.TTSRequest(text="Hello", seed=1000001)


class TestProcessReferenceAudio(unittest.TestCase):
    """Test reference audio processing."""

    @patch("rp_handler.os.path.exists")
    def test_default_audio_exists(self, mock_exists):
        mock_exists.return_value = True
        result = rp_handler.process_reference_audio(None)
        self.assertEqual(result, "input/maya.wav")

    @patch("rp_handler.requests.get")
    @patch("rp_handler.os.path.exists")
    def test_default_audio_download(self, mock_exists, mock_get):
        mock_exists.return_value = False
        mock_response = MagicMock()
        mock_response.content = b"audio_data"
        mock_get.return_value = mock_response

        result = rp_handler.process_reference_audio(None)
        self.assertEqual(result, "input/maya.wav")
        mock_get.assert_called_once()

    @patch("rp_handler.requests.get")
    @patch("rp_handler.tempfile.NamedTemporaryFile")
    def test_url_audio(self, mock_tempfile, mock_get):
        mock_response = MagicMock()
        mock_response.content = b"audio_data"
        mock_get.return_value = mock_response

        mock_file = MagicMock()
        mock_file.name = "/tmp/test.wav"
        mock_tempfile.return_value.__enter__.return_value = mock_file

        result = rp_handler.process_reference_audio("http://example.com/audio.wav")
        self.assertEqual(result, "/tmp/test.wav")
        mock_get.assert_called_once_with("http://example.com/audio.wav")

    @patch("rp_handler.tempfile.NamedTemporaryFile")
    def test_base64_audio(self, mock_tempfile):
        audio_data = b"test_audio_data"
        b64_data = base64.b64encode(audio_data).decode()

        mock_file = MagicMock()
        mock_file.name = "/tmp/test.wav"
        mock_tempfile.return_value.__enter__.return_value = mock_file

        result = rp_handler.process_reference_audio(b64_data)
        self.assertEqual(result, "/tmp/test.wav")
        mock_file.write.assert_called_once_with(audio_data)

    def test_invalid_base64_audio(self):
        with self.assertRaises(ValueError):
            rp_handler.process_reference_audio("invalid_base64!")


class TestModifyWorkflow(unittest.TestCase):
    """Test workflow modification."""

    @patch("builtins.open", new_callable=mock_open, read_data='{"nodes": [{}, {}, {}, {}, {}]}')
    def test_modify_workflow(self, mock_file):
        workflow = rp_handler.modify_workflow("Test text", "/path/to/audio.wav", 0.9, 1.2, 123)

        # Verify the workflow was loaded
        mock_file.assert_called_once_with("workflows/vibevoice_tts.json", "r")

        # Check that nodes were modified
        self.assertEqual(workflow["nodes"][0]["widgets_values"][0], "Test text")
        self.assertEqual(workflow["nodes"][1]["widgets_values"][0], "/path/to/audio.wav")
        self.assertEqual(workflow["nodes"][2]["widgets_values"][0], 0.9)
        self.assertEqual(workflow["nodes"][3]["widgets_values"][0], 1.2)
        self.assertEqual(workflow["nodes"][4]["widgets_values"][0], 123)


class TestExecuteWorkflow(unittest.TestCase):
    """Test workflow execution via websockets."""

    @patch("rp_handler.websockets.connect")
    async def test_execute_workflow_success(self, mock_connect):
        # Mock websocket context manager
        mock_websocket = MagicMock()
        mock_connect.return_value.__aenter__.return_value = mock_websocket

        # Mock successful execution
        mock_websocket.recv.side_effect = [
            json.dumps({"type": "execution_cached"}),
            json.dumps({"type": "execution_success"})
        ]

        result = await rp_handler.execute_workflow({"test": "workflow"})
        self.assertEqual(result, "output/vibevoice_output.wav")

    @patch("rp_handler.websockets.connect")
    async def test_execute_workflow_error(self, mock_connect):
        mock_websocket = MagicMock()
        mock_connect.return_value.__aenter__.return_value = mock_websocket

        mock_websocket.recv.return_value = json.dumps({
            "type": "execution_error",
            "data": {"message": "Test error"}
        })

        with self.assertRaises(Exception):
            await rp_handler.execute_workflow({"test": "workflow"})

    @patch("rp_handler.websockets.connect")
    async def test_execute_workflow_websocket_error(self, mock_connect):
        mock_connect.side_effect = Exception("Connection failed")

        with self.assertRaises(Exception):
            await rp_handler.execute_workflow({"test": "workflow"})


class TestGetAudioOutput(unittest.TestCase):
    """Test audio output processing."""

    @patch("rp_handler.torchaudio.load")
    @patch("builtins.open", new_callable=mock_open, read_data=b"audio_data")
    def test_get_audio_output(self, mock_file, mock_load):
        # Mock torchaudio
        mock_waveform = MagicMock()
        mock_waveform.shape = [1, 44100]  # 1 second at 44100 Hz
        mock_load.return_value = (mock_waveform, 44100)

        result = rp_handler.get_audio_output("/path/to/audio.wav", 123)

        expected_b64 = base64.b64encode(b"audio_data").decode()
        self.assertEqual(result["audio_base64"], expected_b64)
        self.assertEqual(result["duration"], 1.0)
        self.assertEqual(result["sample_rate"], 44100)
        self.assertEqual(result["seed_used"], 123)

    @patch("rp_handler.torchaudio.load")
    def test_get_audio_output_error(self, mock_load):
        mock_load.side_effect = Exception("Load failed")

        with self.assertRaises(Exception):
            rp_handler.get_audio_output("/path/to/audio.wav", 123)


class TestHandler(unittest.TestCase):
    """Test main handler function."""

    @patch("rp_handler.process_reference_audio")
    @patch("rp_handler.modify_workflow")
    @patch("rp_handler.execute_workflow")
    @patch("rp_handler.get_audio_output")
    def test_handler_success(self, mock_get_output, mock_execute, mock_modify, mock_process_audio):
        # Setup mocks
        mock_process_audio.return_value = "/path/to/audio.wav"
        mock_modify.return_value = {"modified": "workflow"}
        mock_execute.return_value = "/output/audio.wav"
        mock_get_output.return_value = {"audio_base64": "b64data", "duration": 2.0}

        event = {
            "input": {
                "text": "Hello world",
                "temperature": 0.9,
                "speed": 1.2,
                "seed": 456
            }
        }

        result = rp_handler.handler(event)

        self.assertEqual(result["audio_base64"], "b64data")
        self.assertEqual(result["duration"], 2.0)
        mock_process_audio.assert_called_once_with(None)
        mock_modify.assert_called_once_with("Hello world", "/path/to/audio.wav", 0.9, 1.2, 456)

    @patch("rp_handler.process_reference_audio")
    def test_handler_validation_error(self, mock_process_audio):
        event = {"input": {"text": ""}}  # Invalid: empty text

        result = rp_handler.handler(event)
        self.assertIn("error", result)

    @patch("rp_handler.process_reference_audio")
    @patch("rp_handler.modify_workflow")
    @patch("rp_handler.execute_workflow")
    def test_handler_execution_error(self, mock_execute, mock_modify, mock_process_audio):
        mock_process_audio.return_value = "/path/to/audio.wav"
        mock_modify.return_value = {"workflow": "data"}
        mock_execute.side_effect = Exception("Execution failed")

        event = {"input": {"text": "Hello"}}

        result = rp_handler.handler(event)
        self.assertIn("error", result)
        self.assertIn("Execution failed", result["error"])

    @patch("rp_handler.os.unlink")
    @patch("rp_handler.process_reference_audio")
    @patch("rp_handler.modify_workflow")
    @patch("rp_handler.execute_workflow")
    @patch("rp_handler.get_audio_output")
    def test_handler_temp_file_cleanup(self, mock_get_output, mock_execute, mock_modify, mock_process_audio, mock_unlink):
        mock_process_audio.return_value = "/tmp/temp_audio.wav"
        mock_modify.return_value = {"workflow": "data"}
        mock_execute.return_value = "/output/audio.wav"
        mock_get_output.return_value = {"audio": "data"}

        event = {"input": {"text": "Hello"}}

        rp_handler.handler(event)

        # Should attempt to cleanup temp file
        mock_unlink.assert_called_once_with("/tmp/temp_audio.wav")


if __name__ == "__main__":
    unittest.main()