.PHONY: test test-unit test-performance test-integration test-all
.PHONY: coverage benchmark clean install install-test
.PHONY: docker-build docker-test docker-clean

# Default target
test: test-unit

# Unit tests
test-unit:
	python run_tests.py unit

# Performance tests
test-performance:
	python run_tests.py performance

# Integration tests
test-integration:
	python run_tests.py integration

# All tests
test-all:
	python run_tests.py all

# Coverage report
coverage:
	python run_tests.py unit --coverage

# Performance benchmarks
benchmark:
	python run_tests.py performance --benchmark

# Install dependencies
install:
	pip install -r requirements.txt

# Install test dependencies
install-test: install
	pip install -r requirements-test.txt

# Docker commands
docker-build:
	docker build -t runpod-worker-test -f Dockerfile.test .

docker-test:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit

docker-clean:
	docker compose -f docker-compose.test.yml down -v --remove-orphans

# Clean up test artifacts
clean:
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	rm -rf tests/__pycache__/
	rm -rf .benchmarks/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

# Development setup
setup: install-test
	pre-commit install

# Lint code
lint:
	flake8 rp_handler.py tests/
	black --check rp_handler.py tests/
	isort --check-only rp_handler.py tests/

# Format code
format:
	black rp_handler.py tests/
	isort rp_handler.py tests/

# Type check
type-check:
	mypy rp_handler.py tests/

# Full CI pipeline
ci: lint type-check test-all coverage

# Help
help:
	@echo "Available targets:"
	@echo "  test-unit        - Run unit tests"
	@echo "  test-performance - Run performance tests"
	@echo "  test-integration - Run integration tests with Docker"
	@echo "  test-all         - Run all test suites"
	@echo "  coverage         - Generate coverage report"
	@echo "  benchmark        - Run performance benchmarks"
	@echo "  install          - Install main dependencies"
	@echo "  install-test     - Install test dependencies"
	@echo "  docker-build     - Build test Docker image"
	@echo "  docker-test      - Run tests in Docker"
	@echo "  docker-clean     - Clean up Docker test environment"
	@echo "  clean            - Clean up test artifacts"
	@echo "  setup            - Set up development environment"
	@echo "  lint             - Lint code"
	@echo "  format           - Format code"
	@echo "  type-check       - Type check code"
	@echo "  ci               - Run full CI pipeline"