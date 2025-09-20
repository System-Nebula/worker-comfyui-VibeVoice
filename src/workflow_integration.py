import json
import os
from typing import Dict, Any, Optional

# Load the base workflow
def load_base_workflow() -> Dict[str, Any]:
    """Load the base LoadAudio-VibeVoiceSS workflow."""
    workflow_path = os.path.join(os.path.dirname(__file__), '..', 'LoadAudio-VibeVoiceSS.json')
    with open(workflow_path, 'r') as f:
        return json.load(f)

# Analyze workflow structure
def analyze_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the workflow and return information about nodes, models, and dependencies."""
    analysis = {
        "nodes": {},
        "models": set(),
        "custom_nodes": set(),
        "dependencies": []
    }

    for node_id, node_data in workflow.items():
        node_type = node_data.get("class_type", "")
        analysis["nodes"][node_id] = {
            "type": node_type,
            "inputs": list(node_data.get("inputs", {}).keys())
        }

        # Identify custom nodes (non-built-in)
        if node_type not in ["LoadAudio", "SaveAudio"]:  # Add more built-ins as needed
            analysis["custom_nodes"].add(node_type)

        # Extract models from inputs
        if "model" in node_data.get("inputs", {}):
            model = node_data["inputs"]["model"]
            if isinstance(model, str):
                analysis["models"].add(model)

    # Dependencies
    if "VibeVoiceSingleSpeakerNode" in analysis["custom_nodes"]:
        analysis["dependencies"].append("ComfyUI-VibeVoice custom nodes (https://github.com/wildminder/ComfyUI-VibeVoice/)")

    return analysis

# Input parameter mapping
INPUT_MAPPING = {
    "text": ("2", "text"),  # node_id, input_key
    "reference_audio": ("3", "audio"),
    "model": ("2", "model"),
    "attention_type": ("2", "attention_type"),
    "diffusion_steps": ("2", "diffusion_steps"),
    "cfg_scale": ("2", "cfg_scale"),
    "temperature": ("2", "temperature"),
    "top_p": ("2", "top_p"),
    "output_prefix": ("5", "filename_prefix")
}

def modify_workflow_for_tts(
    base_workflow: Dict[str, Any],
    text: str,
    reference_audio: str,
    model: str = "VibeVoice-Large",
    voice_settings: Optional[Dict[str, Any]] = None,
    output_prefix: str = "audio/ComfyUI"
) -> Dict[str, Any]:
    """
    Modify the workflow for TTS generation.

    Args:
        base_workflow: The base workflow JSON
        text: The text to synthesize
        reference_audio: Path to reference audio file
        model: TTS model to use
        voice_settings: Additional voice settings (attention_type, diffusion_steps, etc.)
        output_prefix: Prefix for output audio file

    Returns:
        Modified workflow JSON
    """
    # Create a deep copy
    workflow = json.loads(json.dumps(base_workflow))

    # Update text
    workflow["2"]["inputs"]["text"] = text

    # Update reference audio
    workflow["3"]["inputs"]["audio"] = reference_audio

    # Update model
    workflow["2"]["inputs"]["model"] = model

    # Update output prefix
    workflow["5"]["inputs"]["filename_prefix"] = output_prefix

    # Update voice settings
    if voice_settings:
        for setting, value in voice_settings.items():
            if setting in workflow["2"]["inputs"]:
                workflow["2"]["inputs"][setting] = value

    return workflow

def validate_workflow_inputs(workflow: Dict[str, Any]) -> bool:
    """Validate that the workflow has required inputs and links."""
    required_nodes = {"2", "3", "5"}  # VibeVoice, LoadAudio, SaveAudio

    if not all(node in workflow for node in required_nodes):
        return False

    # Check that voice_to_clone links to LoadAudio
    if workflow["2"]["inputs"].get("voice_to_clone") != ["3", 0]:
        return False

    # Check that SaveAudio links to VibeVoice
    if workflow["5"]["inputs"].get("audio") != ["2", 0]:
        return False

    return True

# Main analysis
if __name__ == "__main__":
    workflow = load_base_workflow()
    analysis = analyze_workflow(workflow)

    print("Workflow Analysis:")
    print(f"Nodes: {analysis['nodes']}")
    print(f"Models: {analysis['models']}")
    print(f"Custom Nodes: {analysis['custom_nodes']}")
    print(f"Dependencies: {analysis['dependencies']}")

    print(f"\nWorkflow valid: {validate_workflow_inputs(workflow)}")