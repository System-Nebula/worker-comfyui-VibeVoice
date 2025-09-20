#!/usr/bin/env python3
"""
Test runner script for RunPod worker testing.
Provides different test modes and configurations.
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def run_unit_tests(args):
    """Run unit tests."""
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_rp_handler.py",
        "tests/test_audio_validation.py",
        "-v", "--tb=short"
    ]

    if args.coverage:
        cmd.extend(["--cov=rp_handler", "--cov-report=html"])

    return subprocess.run(cmd, cwd=Path(__file__).parent)


def run_performance_tests(args):
    """Run performance tests."""
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_performance.py",
        "-v", "--tb=short",
        "-m", "performance"
    ]

    if args.benchmark:
        cmd.extend(["--benchmark-only", "--benchmark-save=performance_results"])

    return subprocess.run(cmd, cwd=Path(__file__).parent)


def run_integration_tests(args):
    """Run integration tests with Docker Compose."""
    # Check if Docker Compose is available
    try:
        subprocess.run(["docker", "compose", "version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Docker Compose not available. Running unit tests only.")
        return run_unit_tests(args)

    # Run tests with Docker Compose
    cmd = [
        "docker", "compose",
        "-f", "docker-compose.test.yml",
        "up", "--build", "--abort-on-container-exit"
    ]

    return subprocess.run(cmd, cwd=Path(__file__).parent)


def run_all_tests(args):
    """Run all test suites."""
    print("Running unit tests...")
    result1 = run_unit_tests(args)

    print("\nRunning performance tests...")
    result2 = run_performance_tests(args)

    if result1.returncode == 0 and result2.returncode == 0:
        print("\nAll tests passed!")
        return result2
    else:
        print("\nSome tests failed!")
        return result1 if result1.returncode != 0 else result2


def main():
    parser = argparse.ArgumentParser(description="RunPod Worker Test Runner")
    parser.add_argument(
        "mode",
        choices=["unit", "performance", "integration", "all"],
        default="all",
        nargs="?",
        help="Test mode to run"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run performance benchmarks"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Set up environment
    os.environ.setdefault("PYTHONPATH", str(Path(__file__).parent))

    # Run appropriate test mode
    if args.mode == "unit":
        result = run_unit_tests(args)
    elif args.mode == "performance":
        result = run_performance_tests(args)
    elif args.mode == "integration":
        result = run_integration_tests(args)
    else:  # all
        result = run_all_tests(args)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()