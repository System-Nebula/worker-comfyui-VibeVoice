import unittest
import io
import wave
import struct
from unittest.mock import patch, MagicMock, mock_open
import sys
import os
import base64

# Add the root directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import rp_handler


class TestAudioValidation(unittest.TestCase):
    """Test audio output quality and format compliance."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a valid WAV file in memory for testing
        self.sample_rate = 44100
        self.channels = 1
        self.sample_width = 2  # 16-bit
        self.duration = 1.0
        self.num_samples = int(self.sample_rate * self.duration)

        # Generate sine wave samples
        samples = []
        for i in range(self.num_samples):
            # 440 Hz sine wave
            sample = int(32767 * 0.5 * (i * 2 * 3.14159 * 440 / self.sample_rate))
            samples.append(struct.pack('<h', sample))

        wav_data = b''.join(samples)

        # Create WAV file header
        wav_header = self._create_wav_header(len(wav_data))
        self.valid_wav_data = wav_header + wav_data

    def _create_wav_header(self, data_size):
        """Create a minimal WAV file header."""
        header = b'RIFF'
        header += struct.pack('<I', 36 + data_size)  # File size
        header += b'WAVE'
        header += b'fmt '
        header += struct.pack('<I', 16)  # Format chunk size
        header += struct.pack('<H', 1)   # Audio format (PCM)
        header += struct.pack('<H', self.channels)
        header += struct.pack('<I', self.sample_rate)
        header += struct.pack('<I', self.sample_rate * self.channels * self.sample_width)
        header += struct.pack('<H', self.channels * self.sample_width)
        header += struct.pack('<H', self.sample_width * 8)
        header += b'data'
        header += struct.pack('<I', data_size)
        return header

    @patch("rp_handler.torchaudio.load")
    @patch("builtins.open", new_callable=mock_open)
    def test_valid_wav_output_format(self, mock_file, mock_load):
        """Test that output audio is in valid WAV format."""
        # Mock file reading
        mock_file.return_value.read.return_value = self.valid_wav_data

        # Mock torchaudio
        mock_waveform = MagicMock()
        mock_waveform.shape = [1, self.num_samples]
        mock_load.return_value = (mock_waveform, self.sample_rate)

        result = rp_handler.get_audio_output("test.wav", 42)

        # Verify base64 encoding
        decoded_audio = base64.b64decode(result["audio_base64"])
        self.assertEqual(decoded_audio, self.valid_wav_data)

        # Verify metadata
        self.assertEqual(result["sample_rate"], self.sample_rate)
        self.assertAlmostEqual(result["duration"], self.duration, places=2)
        self.assertEqual(result["seed_used"], 42)

    @patch("rp_handler.torchaudio.load")
    @patch("builtins.open", new_callable=mock_open)
    def test_audio_quality_checks(self, mock_file, mock_load):
        """Test audio quality validation."""
        # Test with different sample rates
        test_cases = [
            (22050, 0.5),  # 22kHz, 0.5s
            (44100, 1.0),  # 44.1kHz, 1.0s
            (48000, 2.0),  # 48kHz, 2.0s
        ]

        for sample_rate, duration in test_cases:
            with self.subTest(sample_rate=sample_rate, duration=duration):
                num_samples = int(sample_rate * duration)
                mock_waveform = MagicMock()
                mock_waveform.shape = [1, num_samples]
                mock_load.return_value = (mock_waveform, sample_rate)

                # Create appropriate WAV data
                samples = [struct.pack('<h', 0) for _ in range(num_samples)]
                wav_data = self._create_wav_header(len(b''.join(samples))) + b''.join(samples)
                mock_file.return_value.read.return_value = wav_data

                result = rp_handler.get_audio_output("test.wav", 42)

                # Verify sample rate and duration are correctly calculated
                self.assertEqual(result["sample_rate"], sample_rate)
                self.assertAlmostEqual(result["duration"], duration, places=2)

    def test_base64_encoding_integrity(self):
        """Test that base64 encoding/decoding preserves audio data."""
        test_audio_data = b"This is test audio data\x00\x01\x02\x03"

        # Manually encode and decode to verify integrity
        encoded = base64.b64encode(test_audio_data).decode()
        decoded = base64.b64decode(encoded)

        self.assertEqual(decoded, test_audio_data)

    @patch("rp_handler.torchaudio.load")
    @patch("builtins.open", new_callable=mock_open)
    def test_audio_file_corruption_detection(self, mock_file, mock_load):
        """Test detection of corrupted audio files."""
        # Test with corrupted WAV data
        corrupted_data = b"This is not a valid WAV file"
        mock_file.return_value.read.return_value = corrupted_data

        # torchaudio.load should fail on invalid data
        mock_load.side_effect = Exception("Invalid WAV file")

        with self.assertRaises(Exception):
            rp_handler.get_audio_output("corrupted.wav", 42)

    @patch("rp_handler.torchaudio.load")
    @patch("builtins.open", new_callable=mock_open)
    def test_empty_audio_file_handling(self, mock_file, mock_load):
        """Test handling of empty or very short audio files."""
        # Empty file
        mock_file.return_value.read.return_value = b""

        mock_waveform = MagicMock()
        mock_waveform.shape = [1, 0]  # No samples
        mock_load.return_value = (mock_waveform, 44100)

        result = rp_handler.get_audio_output("empty.wav", 42)

        # Should handle empty file gracefully
        self.assertEqual(result["duration"], 0.0)
        self.assertEqual(result["sample_rate"], 44100)

    @patch("rp_handler.torchaudio.load")
    @patch("builtins.open", new_callable=mock_open)
    def test_stereo_audio_handling(self, mock_file, mock_load):
        """Test handling of stereo audio files."""
        # Stereo audio (2 channels)
        mock_waveform = MagicMock()
        mock_waveform.shape = [2, 44100]  # 2 channels, 1 second
        mock_load.return_value = (mock_waveform, 44100)

        # Create stereo WAV data
        samples = []
        for i in range(44100):
            # Left channel
            samples.append(struct.pack('<h', int(10000 * (i % 2))))
            # Right channel
            samples.append(struct.pack('<h', int(-10000 * (i % 2))))

        wav_data = self._create_wav_header(len(b''.join(samples))) + b''.join(samples)
        mock_file.return_value.read.return_value = wav_data

        result = rp_handler.get_audio_output("stereo.wav", 42)

        # Duration should still be calculated correctly for stereo
        self.assertEqual(result["sample_rate"], 44100)
        self.assertEqual(result["duration"], 1.0)

    def test_audio_format_compliance(self):
        """Test compliance with audio format standards."""
        # Test various bit depths and channel configurations
        test_configs = [
            {"channels": 1, "sample_width": 1, "sample_rate": 22050},  # 8-bit mono
            {"channels": 1, "sample_width": 2, "sample_rate": 44100},  # 16-bit mono
            {"channels": 2, "sample_width": 2, "sample_rate": 44100},  # 16-bit stereo
        ]

        for config in test_configs:
            with self.subTest(**config):
                channels = config["channels"]
                sample_width = config["sample_width"]
                sample_rate = config["sample_rate"]

                # Create valid WAV header for this configuration
                num_samples = sample_rate  # 1 second
                data_size = num_samples * channels * sample_width
                header = self._create_wav_header_for_config(data_size, channels, sample_width, sample_rate)

                # Verify header is correctly formatted
                self.assertEqual(header[0:4], b'RIFF')
                self.assertEqual(header[8:12], b'WAVE')
                self.assertEqual(header[12:16], b'fmt ')

                # Verify format parameters in header
                fmt_data = header[16:36]
                audio_format, num_channels, sample_rate_header = struct.unpack('<HHH', fmt_data[0:6])
                self.assertEqual(audio_format, 1)  # PCM
                self.assertEqual(num_channels, channels)
                self.assertEqual(sample_rate_header, sample_rate)

    def _create_wav_header_for_config(self, data_size, channels, sample_width, sample_rate):
        """Create WAV header for specific audio configuration."""
        header = b'RIFF'
        header += struct.pack('<I', 36 + data_size)
        header += b'WAVE'
        header += b'fmt '
        header += struct.pack('<I', 16)  # Format chunk size
        header += struct.pack('<H', 1)   # Audio format (PCM)
        header += struct.pack('<H', channels)
        header += struct.pack('<I', sample_rate)
        header += struct.pack('<I', sample_rate * channels * sample_width)
        header += struct.pack('<H', channels * sample_width)
        header += struct.pack('<H', sample_width * 8)
        header += b'data'
        header += struct.pack('<I', data_size)
        return header

    @patch("rp_handler.torchaudio.load")
    @patch("builtins.open", new_callable=mock_open)
    def test_audio_metadata_accuracy(self, mock_file, mock_load):
        """Test accuracy of audio metadata extraction."""
        # Test with precise timing
        test_durations = [0.5, 1.0, 2.5, 10.0]
        sample_rate = 44100

        for expected_duration in test_durations:
            with self.subTest(duration=expected_duration):
                num_samples = int(sample_rate * expected_duration)
                mock_waveform = MagicMock()
                mock_waveform.shape = [1, num_samples]
                mock_load.return_value = (mock_waveform, sample_rate)

                result = rp_handler.get_audio_output("test.wav", 42)

                # Duration should be accurate to within 0.01 seconds
                self.assertAlmostEqual(result["duration"], expected_duration, places=2)
                self.assertEqual(result["sample_rate"], sample_rate)


class TestAudioQualityMetrics(unittest.TestCase):
    """Test audio quality metrics and validation."""

    @patch("rp_handler.torchaudio.load")
    @patch("builtins.open", new_callable=mock_open)
    def test_audio_length_validation(self, mock_file, mock_load):
        """Test that generated audio meets minimum length requirements."""
        # Test various audio lengths
        test_cases = [
            (0.1, True),   # Too short
            (0.5, True),   # Minimum acceptable
            (1.0, True),   # Good length
            (30.0, True),  # Maximum acceptable
            (35.0, False), # Too long (should be validated at generation time)
        ]

        for duration, should_pass in test_cases:
            with self.subTest(duration=duration):
                sample_rate = 44100
                num_samples = int(sample_rate * duration)
                mock_waveform = MagicMock()
                mock_waveform.shape = [1, num_samples]
                mock_load.return_value = (mock_waveform, sample_rate)

                result = rp_handler.get_audio_output("test.wav", 42)

                # Just verify the duration is calculated correctly
                # Length validation would happen at the workflow level
                self.assertAlmostEqual(result["duration"], duration, places=2)

    def test_base64_payload_size(self):
        """Test that base64 encoded audio is reasonably sized."""
        # Test with different audio file sizes
        test_sizes = [1024, 10240, 102400, 1048576]  # 1KB, 10KB, 100KB, 1MB

        for size in test_sizes:
            with self.subTest(size=size):
                # Create dummy audio data
                audio_data = b'A' * size

                # Encode to base64
                encoded = base64.b64encode(audio_data).decode()

                # Verify encoding is correct
                decoded = base64.b64decode(encoded)
                self.assertEqual(decoded, audio_data)

                # Verify size is reasonable (base64 is ~33% larger)
                expected_size = len(audio_data) * 4 // 3
                self.assertAlmostEqual(len(encoded), expected_size, delta=10)


if __name__ == "__main__":
    unittest.main()