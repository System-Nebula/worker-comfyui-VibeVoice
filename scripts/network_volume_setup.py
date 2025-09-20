#!/usr/bin/env python3
"""
Network Volume Setup for RunPod VibeVoice TTS Worker

This script configures network volumes for persistent storage of models,
cache, and other data that needs to persist across container restarts.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List

class NetworkVolumeSetup:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.runpod_dir = self.project_root / ".runpod"

    def create_model_volume_config(self) -> Dict[str, Any]:
        """Create model storage volume configuration"""

        model_volume = {
            "name": "vibevoice-models",
            "description": "Persistent storage for TTS models and weights",
            "sizeGb": 100,
            "mountPath": "/workspace/models",
            "filesystem": "ext4",
            "performance": "high",
            "backup": {
                "enabled": True,
                "schedule": "daily",
                "retentionDays": 30,
                "type": "incremental"
            },
            "encryption": {
                "enabled": True,
                "algorithm": "AES256"
            },
            "directories": [
                "tts/VibeVoice",
                "checkpoints",
                "loras",
                "embeddings"
            ]
        }

        return model_volume

    def create_cache_volume_config(self) -> Dict[str, Any]:
        """Create cache storage volume configuration"""

        cache_volume = {
            "name": "vibevoice-cache",
            "description": "Fast storage for caches and temporary data",
            "sizeGb": 50,
            "mountPath": "/workspace/.cache",
            "filesystem": "ext4",
            "performance": "high",
            "persistence": "session",
            "directories": [
                "pip",
                "conda",
                "huggingface",
                "torch",
                "workflows",
                "http"
            ]
        }

        return cache_volume

    def create_output_volume_config(self) -> Dict[str, Any]:
        """Create output storage volume configuration"""

        output_volume = {
            "name": "vibevoice-outputs",
            "description": "Storage for generated audio outputs and logs",
            "sizeGb": 25,
            "mountPath": "/workspace/outputs",
            "filesystem": "ext4",
            "performance": "standard",
            "retention": {
                "enabled": True,
                "maxAgeDays": 7,
                "autoCleanup": True
            },
            "directories": [
                "audio",
                "logs",
                "temp"
            ]
        }

        return output_volume

    def create_config_volume_config(self) -> Dict[str, Any]:
        """Create configuration volume configuration"""

        config_volume = {
            "name": "vibevoice-config",
            "description": "Storage for configuration files and settings",
            "sizeGb": 5,
            "mountPath": "/workspace/config",
            "filesystem": "ext4",
            "performance": "standard",
            "backup": {
                "enabled": True,
                "schedule": "weekly",
                "retentionDays": 90
            },
            "files": [
                "workflow_defaults.json",
                "model_configs.json",
                "scaling_profiles.json"
            ]
        }

        return config_volume

    def create_volume_mounts_config(self) -> List[Dict[str, Any]]:
        """Create volume mounts configuration"""

        mounts = [
            {
                "volume": "vibevoice-models",
                "mountPath": "/workspace/models",
                "readOnly": False,
                "mountOptions": ["rw", "relatime"]
            },
            {
                "volume": "vibevoice-cache",
                "mountPath": "/workspace/.cache",
                "readOnly": False,
                "mountOptions": ["rw", "relatime", "noatime"]
            },
            {
                "volume": "vibevoice-outputs",
                "mountPath": "/workspace/outputs",
                "readOnly": False,
                "mountOptions": ["rw", "relatime"]
            },
            {
                "volume": "vibevoice-config",
                "mountPath": "/workspace/config",
                "readOnly": False,
                "mountOptions": ["rw", "relatime"]
            }
        ]

        return mounts

    def create_snapshot_config(self) -> Dict[str, Any]:
        """Create volume snapshot configuration"""

        snapshot_config = {
            "enabled": True,
            "schedule": "0 2 * * *",  # Daily at 2 AM
            "retention": {
                "daily": 7,
                "weekly": 4,
                "monthly": 12
            },
            "volumes": [
                "vibevoice-models",
                "vibevoice-config"
            ],
            "preSnapshotCommands": [
                "sync",
                "/workspace/scripts/backup_models.sh"
            ],
            "postSnapshotCommands": [
                "/workspace/scripts/verify_snapshot.sh"
            ]
        }

        return snapshot_config

    def generate_volume_config(self) -> Dict[str, Any]:
        """Generate complete network volume configuration"""

        config = {
            "version": "1.0",
            "description": "Network volume configuration for VibeVoice TTS worker",
            "volumes": [
                self.create_model_volume_config(),
                self.create_cache_volume_config(),
                self.create_output_volume_config(),
                self.create_config_volume_config()
            ],
            "mounts": self.create_volume_mounts_config(),
            "snapshots": self.create_snapshot_config(),
            "monitoring": {
                "enabled": True,
                "alerts": {
                    "lowSpaceThresholdPercent": 80,
                    "highUsageThresholdPercent": 90
                },
                "metrics": [
                    "volume_size_bytes",
                    "volume_used_bytes",
                    "volume_available_bytes",
                    "inode_usage_percent"
                ]
            }
        }

        return config

    def save_config(self, config: Dict[str, Any], filename: str = "network_volumes.json"):
        """Save network volume configuration to file"""

        config_file = self.runpod_dir / filename
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"Network volume configuration saved to {config_file}")
        return config_file

def main():
    setup = NetworkVolumeSetup()

    # Generate complete configuration
    config = setup.generate_volume_config()

    # Save configuration
    config_file = setup.save_config(config)

    print("\nNetwork Volume Configuration Summary:")
    print(f"   Total Volumes: {len(config['volumes'])}")
    print(f"   Total Storage: {sum(v['sizeGb'] for v in config['volumes'])}GB")

    print("\nVolume Details:")
    for volume in config['volumes']:
        backup_status = "Enabled" if volume.get('backup', {}).get('enabled', False) else "Disabled"
        print(f"   • {volume['name']}: {volume['sizeGb']}GB - {volume['description']}")
        print(f"     Mount: {volume['mountPath']} | Backup: {backup_status}")

    print("\nMount Points:")
    for mount in config['mounts']:
        read_only = " (RO)" if mount.get('readOnly', False) else ""
        print(f"   • {mount['mountPath']}{read_only}")

    print("\nSnapshot Configuration:")
    snapshot = config['snapshots']
    print(f"   • Schedule: {snapshot['schedule']}")
    print(f"   • Retention: {snapshot['retention']['daily']} daily, {snapshot['retention']['weekly']} weekly")

if __name__ == "__main__":
    main()