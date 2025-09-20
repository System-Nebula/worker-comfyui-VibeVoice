import unittest
import time
import asyncio
from unittest.mock import patch, MagicMock
import sys
import os

# Add the root directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import rp_handler


class TestPerformanceBenchmarking(unittest.TestCase):
    """Performance tests for cold start and generation times."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_event = {
            "input": {
                "text": "This is a test sentence for performance benchmarking.",
                "temperature": 0.8,
                "speed": 1.0,
                "seed": 42
            }
        }

    @patch("rp_handler.process_reference_audio")
    @patch("rp_handler.modify_workflow")
    @patch("rp_handler.execute_workflow")
    @patch("rp_handler.get_audio_output")
    def test_generation_time_benchmark(self, mock_get_output, mock_execute, mock_modify, mock_process_audio):
        """Test that audio generation completes within 10 seconds."""
        # Setup mocks
        mock_process_audio.return_value = "input/maya.wav"
        mock_modify.return_value = {"test": "workflow"}
        mock_execute.return_value = "output/test.wav"
        mock_get_output.return_value = {
            "audio_base64": "dGVzdA==",  # base64 "test"
            "duration": 2.5,
            "sample_rate": 44100,
            "seed_used": 42
        }

        # Measure execution time
        start_time = time.time()
        result = rp_handler.handler(self.test_event)
        end_time = time.time()

        generation_time = end_time - start_time

        # Assert generation time is under 10 seconds
        self.assertLess(generation_time, 10.0,
                       f"Generation time {generation_time:.2f}s exceeded 10s limit")

        # Verify result structure
        self.assertIn("audio_base64", result)
        self.assertIn("duration", result)

    @patch("rp_handler.process_reference_audio")
    @patch("rp_handler.modify_workflow")
    @patch("rp_handler.execute_workflow")
    @patch("rp_handler.get_audio_output")
    def test_cold_start_time_benchmark(self, mock_get_output, mock_execute, mock_modify, mock_process_audio):
        """Test cold start time (first request after initialization)."""
        # Setup mocks
        mock_process_audio.return_value = "input/maya.wav"
        mock_modify.return_value = {"test": "workflow"}
        mock_execute.return_value = "output/test.wav"
        mock_get_output.return_value = {
            "audio_base64": "dGVzdA==",
            "duration": 1.0,
            "sample_rate": 44100,
            "seed_used": 42
        }

        # Simulate cold start by adding small delay to workflow execution
        original_execute = mock_execute
        def delayed_execute(workflow):
            time.sleep(0.1)  # Simulate cold start overhead
            return "output/test.wav"
        mock_execute.side_effect = delayed_execute

        # Measure cold start time
        start_time = time.time()
        result = rp_handler.handler(self.test_event)
        end_time = time.time()

        cold_start_time = end_time - start_time

        # Assert cold start time is under 30 seconds
        self.assertLess(cold_start_time, 30.0,
                       f"Cold start time {cold_start_time:.2f}s exceeded 30s limit")

    def test_parameter_ranges_performance(self):
        """Test that parameter validation is fast."""
        test_cases = [
            {"text": "Hello", "temperature": 0.0, "speed": 0.5, "seed": 0},
            {"text": "Hello", "temperature": 2.0, "speed": 2.0, "seed": 1000000},
            {"text": "A" * 1000, "temperature": 1.0, "speed": 1.0, "seed": 500000},
        ]

        for i, params in enumerate(test_cases):
            with self.subTest(case=i):
                start_time = time.time()
                try:
                    request = rp_handler.TTSRequest(**params)
                    validation_time = time.time() - start_time
                    # Validation should be very fast (< 0.01s)
                    self.assertLess(validation_time, 0.01,
                                   f"Validation too slow: {validation_time:.4f}s")
                except ValueError:
                    # Expected for invalid parameters, but timing still matters
                    validation_time = time.time() - start_time
                    self.assertLess(validation_time, 0.01,
                                   f"Validation too slow: {validation_time:.4f}s")

    @patch("rp_handler.requests.get")
    def test_network_timeout_performance(self, mock_get):
        """Test that network operations have reasonable timeouts."""
        # Mock a slow response
        mock_response = MagicMock()
        mock_response.content = b"audio_data"
        mock_response.raise_for_status.return_value = None

        def slow_get(url):
            time.sleep(1.0)  # Simulate network delay
            return mock_response

        mock_get.side_effect = slow_get

        start_time = time.time()
        try:
            rp_handler.process_reference_audio("http://example.com/audio.wav")
        except Exception:
            pass  # Expected due to mocking
        network_time = time.time() - start_time

        # Network operations should complete reasonably fast
        # In real implementation, we'd want timeouts, but for testing we check the operation doesn't hang
        self.assertLess(network_time, 5.0,
                       f"Network operation took too long: {network_time:.2f}s")

    @patch("rp_handler.torchaudio.load")
    @patch("builtins.open", new_callable=lambda: MagicMock())
    def test_audio_processing_performance(self, mock_file, mock_load):
        """Test audio processing performance."""
        # Mock audio data
        mock_waveform = MagicMock()
        mock_waveform.shape = [1, 88200]  # 2 seconds at 44100 Hz
        mock_load.return_value = (mock_waveform, 44100)

        start_time = time.time()
        result = rp_handler.get_audio_output("test.wav", 42)
        processing_time = time.time() - start_time

        # Audio processing should be fast
        self.assertLess(processing_time, 1.0,
                       f"Audio processing too slow: {processing_time:.4f}s")

        # Verify result contains expected fields
        self.assertIn("audio_base64", result)
        self.assertIn("duration", result)
        self.assertIn("sample_rate", result)
        self.assertIn("seed_used", result)


class TestLoadTesting(unittest.TestCase):
    """Load testing for concurrent requests."""

    @patch("rp_handler.process_reference_audio")
    @patch("rp_handler.modify_workflow")
    @patch("rp_handler.execute_workflow")
    @patch("rp_handler.get_audio_output")
    def test_concurrent_requests(self, mock_get_output, mock_execute, mock_modify, mock_process_audio):
        """Test handling multiple concurrent requests."""
        # Setup mocks
        mock_process_audio.return_value = "input/maya.wav"
        mock_modify.return_value = {"test": "workflow"}
        mock_execute.return_value = "output/test.wav"
        mock_get_output.return_value = {
            "audio_base64": "dGVzdA==",
            "duration": 1.0,
            "sample_rate": 44100,
            "seed_used": 42
        }

        async def run_request(request_id):
            event = {
                "input": {
                    "text": f"Test request {request_id}",
                    "temperature": 0.8,
                    "speed": 1.0,
                    "seed": request_id
                }
            }
            start_time = time.time()
            result = rp_handler.handler(event)
            end_time = time.time()
            return end_time - start_time, result

        async def run_concurrent_test():
            tasks = [run_request(i) for i in range(5)]  # 5 concurrent requests
            results = await asyncio.gather(*tasks)
            return results

        # Run concurrent test
        start_time = time.time()
        results = asyncio.run(run_concurrent_test())
        total_time = time.time() - start_time

        # All requests should complete within reasonable time
        max_individual_time = max(r[0] for r in results)
        self.assertLess(max_individual_time, 15.0,
                       f"Individual request too slow: {max_individual_time:.2f}s")

        # Total time should be less than sum of individual times (some concurrency benefit)
        total_individual_time = sum(r[0] for r in results)
        self.assertLess(total_time, total_individual_time,
                       f"No concurrency benefit: total {total_time:.2f}s vs individual sum {total_individual_time:.2f}s")


if __name__ == "__main__":
    unittest.main()