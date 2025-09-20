#!/usr/bin/env python3
"""
RunPod Serverless Deployment Script for VibeVoice TTS Worker

This script handles the deployment of the VibeVoice TTS worker to RunPod serverless
with optimized configurations for GPU inference, caching, and auto-scaling.
"""

import os
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

class RunPodDeployer:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.runpod_dir = self.project_root / ".runpod"
        self.config_file = self.runpod_dir / "hub.json"

    def load_config(self) -> Dict[str, Any]:
        """Load RunPod configuration from hub.json"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")

        with open(self.config_file, 'r') as f:
            return json.load(f)

    def validate_deployment(self) -> bool:
        """Validate deployment prerequisites"""
        required_files = [
            "rp_handler.py",
            "Dockerfile",
            "requirements.txt",
            "workflows/vibevoice_tts.json"
        ]

        missing_files = []
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)

        if missing_files:
            print(f"Missing required files: {', '.join(missing_files)}")
            return False

        print("All required files present")
        return True

    def build_docker_image(self, tag: str = "latest") -> bool:
        """Build Docker image for deployment"""
        image_name = f"vibevoice-tts-worker:{tag}"

        print(f"Building Docker image: {image_name}")

        try:
            cmd = [
                "docker", "build",
                "-t", image_name,
                "-f", str(self.project_root / "Dockerfile"),
                str(self.project_root)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)

            if result.returncode != 0:
                print(f"Docker build failed: {result.stderr}")
                return False

            print("Docker image built successfully")
            return True

        except Exception as e:
            print(f"Error building Docker image: {e}")
            return False

    def push_to_registry(self, registry: str, tag: str = "latest") -> bool:
        """Push Docker image to registry"""
        image_name = f"vibevoice-tts-worker:{tag}"
        full_image_name = f"{registry}/{image_name}"

        print(f"Pushing image to registry: {full_image_name}")

        try:
            # Tag the image
            tag_cmd = ["docker", "tag", image_name, full_image_name]
            subprocess.run(tag_cmd, check=True, cwd=self.project_root)

            # Push the image
            push_cmd = ["docker", "push", full_image_name]
            subprocess.run(push_cmd, check=True, cwd=self.project_root)

            print("Image pushed successfully")
            return True

        except subprocess.CalledProcessError as e:
            print(f"Error pushing image: {e}")
            return False

    def deploy_serverless(self, config: Dict[str, Any]) -> bool:
        """Deploy to RunPod serverless"""
        print("Deploying to RunPod serverless...")

        # This would typically use RunPod CLI or API
        # For now, we'll create a deployment configuration file

        deployment_config = {
            "name": "vibevoice-tts-endpoint",
            "image": "runpod/vibevoice-tts-worker:latest",
            "gpuType": config["config"]["gpuIds"],
            "gpuCount": config["config"]["gpuCount"],
            "containerDiskInGb": config["config"]["containerDiskInGb"],
            "minVram": config["config"].get("minVram", 8192),
            "maxVram": config["config"].get("maxVram", 24576),
            "env": config["config"]["env"],
            "scaling": {
                "minInstances": 1,
                "maxInstances": 5,
                "targetConcurrency": 2
            },
            "networkVolume": {
                "enabled": True,
                "sizeGb": 100,
                "mountPath": "/workspace/models"
            }
        }

        # Save deployment configuration
        deploy_file = self.runpod_dir / "deployment.json"
        with open(deploy_file, 'w') as f:
            json.dump(deployment_config, f, indent=2)

        print(f"Deployment configuration saved to {deploy_file}")
        print("Next steps:")
        print("1. Push your Docker image to a registry")
        print("2. Use RunPod CLI or web interface to deploy")
        print("3. Configure auto-scaling based on your needs")

        return True

    def setup_network_volume(self) -> bool:
        """Setup network volume configuration for persistent storage"""
        volume_config = {
            "name": "vibevoice-models-volume",
            "sizeGb": 100,
            "mountPath": "/workspace/models",
            "persistence": "persistent",
            "backup": {
                "enabled": True,
                "schedule": "daily",
                "retentionDays": 30
            }
        }

        volume_file = self.runpod_dir / "network-volume.json"
        with open(volume_file, 'w') as f:
            json.dump(volume_config, f, indent=2)

        print(f"Network volume configuration saved to {volume_file}")
        return True

    def optimize_for_production(self) -> bool:
        """Apply production optimizations"""
        optimizations = {
            "model_cache": {
                "enabled": True,
                "max_size_gb": 20,
                "preload_models": ["VibeVoice-Large"],
                "cache_strategy": "LRU"
            },
            "gpu_optimization": {
                "enable_tensor_cores": True,
                "memory_efficient_loading": True,
                "gradient_checkpointing": False,
                "mixed_precision": "fp16"
            },
            "network_optimization": {
                "enable_compression": True,
                "connection_pooling": True,
                "keep_alive_timeout": 300
            }
        }

        opt_file = self.runpod_dir / "optimizations.json"
        with open(opt_file, 'w') as f:
            json.dump(optimizations, f, indent=2)

        print(f"Production optimizations saved to {opt_file}")
        return True

def main():
    parser = argparse.ArgumentParser(description="Deploy VibeVoice TTS to RunPod")
    parser.add_argument("--registry", help="Docker registry URL")
    parser.add_argument("--tag", default="latest", help="Docker image tag")
    parser.add_argument("--skip-build", action="store_true", help="Skip Docker build")
    parser.add_argument("--skip-push", action="store_true", help="Skip Docker push")

    args = parser.parse_args()

    deployer = RunPodDeployer()

    # Validate deployment
    if not deployer.validate_deployment():
        return 1

    # Load configuration
    try:
        config = deployer.load_config()
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return 1

    # Build Docker image
    if not args.skip_build:
        if not deployer.build_docker_image(args.tag):
            return 1

    # Push to registry
    if args.registry and not args.skip_push:
        if not deployer.push_to_registry(args.registry, args.tag):
            return 1

    # Setup network volume
    deployer.setup_network_volume()

    # Apply production optimizations
    deployer.optimize_for_production()

    # Deploy to serverless
    if deployer.deploy_serverless(config):
        print("\nDeployment preparation completed!")
        print("Use the generated configuration files to complete deployment via RunPod CLI or web interface.")
        return 0
    else:
        return 1

if __name__ == "__main__":
    exit(main())