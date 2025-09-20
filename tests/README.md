# RunPod Worker Testing Framework

This directory contains comprehensive testing and validation for the RunPod worker that handles VibeVoice TTS requests.

## Test Structure

### Unit Tests (`test_rp_handler.py`)
- **TTSRequest validation**: Tests for input parameter validation (text length, temperature, speed, seed ranges)
- **Reference audio processing**: Tests for base64, URL, and default audio handling
- **Workflow modification**: Tests for ComfyUI workflow parameter injection
- **WebSocket execution**: Tests for workflow execution via ComfyUI websockets
- **Audio output processing**: Tests for audio file reading and base64 encoding
- **Error handling**: Tests for various failure scenarios and edge cases

### Performance Tests (`test_performance.py`)
- **Generation time benchmarking**: Ensures audio generation completes within 10 seconds
- **Cold start time benchmarking**: Ensures first request completes within 30 seconds
- **Parameter validation performance**: Ensures validation is fast (< 0.01s)
- **Network operation timeouts**: Tests for reasonable network operation timing
- **Concurrent request handling**: Tests for multi-request performance

### Audio Validation Tests (`test_audio_validation.py`)
- **WAV format compliance**: Validates output audio format and headers
- **Audio quality checks**: Tests sample rates, bit depths, and channel configurations
- **Base64 encoding integrity**: Ensures audio data preservation through encoding/decoding
- **Metadata accuracy**: Validates duration and sample rate calculations
- **Format standards compliance**: Tests adherence to audio format specifications

## Running Tests

### Local Testing

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Run all tests
python run_tests.py all

# Run specific test suites
python run_tests.py unit              # Unit tests only
python run_tests.py performance       # Performance tests only
python run_tests.py integration       # Integration tests with Docker

# Generate coverage report
python run_tests.py unit --coverage

# Run performance benchmarks
python run_tests.py performance --benchmark
```

### Using Make

```bash
# Quick commands
make test              # Run unit tests
make test-all          # Run all test suites
make coverage          # Generate coverage report
make benchmark         # Run performance benchmarks

# Development setup
make install-test      # Install all dependencies
make setup            # Set up development environment
make lint             # Lint code
make format           # Format code
```

### Docker Testing

```bash
# Build and run integration tests
make docker-test

# Build test image only
make docker-build

# Clean up Docker environment
make docker-clean
```

## Test Configuration

### pytest.ini
- Configures test discovery and execution
- Sets up coverage reporting
- Defines test markers for different test types
- Configures warning filters

### Docker Compose Setup
- `docker-compose.test.yml`: Defines ComfyUI and test runner services
- `Dockerfile.test`: Test runner container with all dependencies
- Health checks ensure ComfyUI is ready before running tests

## Performance Requirements

The tests validate that the RunPod worker meets these performance targets:

- **Cold start time**: < 30 seconds (first request after initialization)
- **Generation time**: < 10 seconds per audio generation
- **Parameter validation**: < 0.01 seconds
- **Concurrent requests**: Efficient handling of multiple simultaneous requests

## Audio Quality Standards

Generated audio must meet these quality standards:

- **Format**: WAV format compliance
- **Sample rates**: Support for 22kHz, 44.1kHz, 48kHz
- **Bit depth**: 16-bit PCM
- **Channels**: Mono and stereo support
- **Base64 encoding**: Lossless encoding/decoding
- **Metadata accuracy**: Precise duration and sample rate reporting

## Test Resources

- `test_resources/`: Directory for test fixtures and sample files
- Sample audio files for validation testing
- Mock workflows for unit testing

## CI/CD Integration

The test suite is designed for CI/CD pipelines:

```bash
# Full CI pipeline
make ci

# This runs:
# - Code linting (flake8)
# - Type checking (mypy)
# - All test suites
# - Coverage reporting
```

## Adding New Tests

### Unit Tests
Add test methods to `test_rp_handler.py` following the existing patterns:
- Use descriptive test method names
- Mock external dependencies
- Test both success and failure cases

### Performance Tests
Add benchmark methods to `test_performance.py`:
- Use timing assertions
- Test realistic scenarios
- Include concurrent load testing

### Audio Validation Tests
Add validation methods to `test_audio_validation.py`:
- Test format compliance
- Validate quality metrics
- Check encoding integrity

## Troubleshooting

### Common Issues

1. **ComfyUI not ready**: Wait for health check or run `make docker-test`
2. **Missing dependencies**: Run `make install-test`
3. **Performance test failures**: Check system resources and GPU availability
4. **Audio validation failures**: Verify torchaudio installation

### Debug Mode

```bash
# Verbose test output
python run_tests.py all --verbose

# Run specific test with debugging
python -m pytest tests/test_rp_handler.py::TestHandler::test_handler_success -v -s
```

## Contributing

When adding new features to the RunPod worker:

1. Add corresponding unit tests
2. Update performance tests if timing requirements change
3. Add audio validation tests for new audio features
4. Update this README with new test information
5. Ensure all tests pass before submitting PR