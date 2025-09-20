#!/usr/bin/env python3
"""
Auto-scaling Configuration for RunPod VibeVoice TTS Worker

This script configures auto-scaling parameters for optimal GPU utilization
and cost efficiency based on workload patterns.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List

class AutoScaler:
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.runpod_dir = self.project_root / ".runpod"

    def create_scaling_profile(self, profile_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a scaling profile configuration"""

        profile = {
            "name": profile_name,
            "description": config.get("description", f"Auto-scaling profile for {profile_name}"),
            "scaling": {
                "minInstances": config.get("min_instances", 1),
                "maxInstances": config.get("max_instances", 5),
                "targetConcurrency": config.get("target_concurrency", 2),
                "scaleUpThreshold": config.get("scale_up_threshold", 0.8),
                "scaleDownThreshold": config.get("scale_down_threshold", 0.3),
                "scaleUpCooldownSeconds": config.get("scale_up_cooldown", 60),
                "scaleDownCooldownSeconds": config.get("scale_down_cooldown", 300)
            },
            "metrics": {
                "cpuUtilization": config.get("cpu_threshold", 70),
                "memoryUtilization": config.get("memory_threshold", 80),
                "gpuUtilization": config.get("gpu_threshold", 75),
                "queueDepth": config.get("queue_depth_threshold", 10)
            },
            "schedules": config.get("schedules", [])
        }

        return profile

    def generate_scaling_profiles(self) -> List[Dict[str, Any]]:
        """Generate predefined scaling profiles for different use cases"""

        profiles = []

        # Development profile - cost optimized
        dev_config = {
            "description": "Development environment with minimal scaling",
            "min_instances": 1,
            "max_instances": 2,
            "target_concurrency": 1,
            "scale_up_threshold": 0.9,
            "scale_down_threshold": 0.2,
            "cpu_threshold": 80,
            "memory_threshold": 85,
            "gpu_threshold": 80,
            "queue_depth_threshold": 5
        }
        profiles.append(self.create_scaling_profile("development", dev_config))

        # Production profile - balanced performance/cost
        prod_config = {
            "description": "Production environment with balanced scaling",
            "min_instances": 2,
            "max_instances": 10,
            "target_concurrency": 3,
            "scale_up_threshold": 0.7,
            "scale_down_threshold": 0.4,
            "cpu_threshold": 70,
            "memory_threshold": 80,
            "gpu_threshold": 75,
            "queue_depth_threshold": 15
        }
        profiles.append(self.create_scaling_profile("production", prod_config))

        # High-throughput profile - performance optimized
        ht_config = {
            "description": "High-throughput environment for peak loads",
            "min_instances": 5,
            "max_instances": 20,
            "target_concurrency": 5,
            "scale_up_threshold": 0.6,
            "scale_down_threshold": 0.5,
            "cpu_threshold": 60,
            "memory_threshold": 75,
            "gpu_threshold": 70,
            "queue_depth_threshold": 25
        }
        profiles.append(self.create_scaling_profile("high-throughput", ht_config))

        # Cost-optimized profile - minimal resources
        cost_config = {
            "description": "Cost-optimized for low-traffic periods",
            "min_instances": 1,
            "max_instances": 3,
            "target_concurrency": 1,
            "scale_up_threshold": 0.95,
            "scale_down_threshold": 0.1,
            "cpu_threshold": 90,
            "memory_threshold": 90,
            "gpu_threshold": 85,
            "queue_depth_threshold": 3
        }
        profiles.append(self.create_scaling_profile("cost-optimized", cost_config))

        return profiles

    def create_time_based_schedules(self) -> List[Dict[str, Any]]:
        """Create time-based scaling schedules"""

        schedules = [
            {
                "name": "business-hours",
                "description": "Scale up during business hours",
                "cronExpression": "0 9 * * 1-5",  # Monday-Friday 9 AM
                "profile": "production",
                "enabled": True
            },
            {
                "name": "off-hours",
                "description": "Scale down during off-hours",
                "cronExpression": "0 18 * * 1-5",  # Monday-Friday 6 PM
                "profile": "cost-optimized",
                "enabled": True
            },
            {
                "name": "weekend",
                "description": "Weekend scaling profile",
                "cronExpression": "0 0 * * 0,6",  # Saturday-Sunday midnight
                "profile": "development",
                "enabled": True
            }
        ]

        return schedules

    def generate_autoscale_config(self) -> Dict[str, Any]:
        """Generate complete auto-scaling configuration"""

        config = {
            "version": "1.0",
            "description": "Auto-scaling configuration for VibeVoice TTS worker",
            "defaultProfile": "production",
            "profiles": self.generate_scaling_profiles(),
            "schedules": self.create_time_based_schedules(),
            "advanced": {
                "enablePredictiveScaling": True,
                "predictionHorizonMinutes": 30,
                "enableSpotInstances": False,
                "fallbackToOnDemand": True,
                "healthCheckIntervalSeconds": 30,
                "maxInstanceLifetimeHours": 24
            }
        }

        return config

    def save_config(self, config: Dict[str, Any], filename: str = "autoscale.json"):
        """Save auto-scaling configuration to file"""

        config_file = self.runpod_dir / filename
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"Auto-scaling configuration saved to {config_file}")
        return config_file

def main():
    scaler = AutoScaler()

    # Generate complete configuration
    config = scaler.generate_autoscale_config()

    # Save configuration
    config_file = scaler.save_config(config)

    print("\nAuto-scaling Configuration Summary:")
    print(f"   Default Profile: {config['defaultProfile']}")
    print(f"   Profiles: {len(config['profiles'])}")
    print(f"   Schedules: {len(config['schedules'])}")

    print("\nAvailable Profiles:")
    for profile in config['profiles']:
        scaling = profile['scaling']
        print(f"   • {profile['name']}: {scaling['minInstances']}-{scaling['maxInstances']} instances")
        print(f"     Target concurrency: {scaling['targetConcurrency']}")

    print("\nScheduled Scaling:")
    for schedule in config['schedules']:
        print(f"   • {schedule['name']}: {schedule['cronExpression']} → {schedule['profile']}")

if __name__ == "__main__":
    main()