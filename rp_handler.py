#!/usr/bin/env python3

"""
RunPod handler for ComfyUI and VibeVoice integration.
"""

import json
import os
import base64
import tempfile
import requests
from typing import Dict, Any, Optional
import asyncio
import websockets
from pydantic import BaseModel, Field

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    reference_audio: Optional[str] = None
    temperature: float = Field(0.8, ge=0.0, le=2.0)
    speed: float = Field(1.0, ge=0.5, le=2.0)
    seed: int = Field(42, ge=0, le=1000000)

def process_reference_audio(ref_audio: Optional[str]) -> str:
    """Process reference audio: handle base64, URL, or use default."""
    if not ref_audio:
        default_path = "input/maya.wav"
        if os.path.exists(default_path):
            return default_path
        else:
            # Download default if not present
            response = requests.get("https://example.com/maya.wav")  # Replace with actual URL
            with open(default_path, "wb") as f:
                f.write(response.content)
            return default_path

    if ref_audio.startswith("http"):
        # Download from URL
        response = requests.get(ref_audio)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(response.content)
            return f.name
    else:
        # Assume base64
        try:
            audio_data = base64.b64decode(ref_audio)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                return f.name
        except Exception:
            raise ValueError("Invalid base64 reference audio")

def modify_workflow(text: str, ref_audio_path: str, temperature: float, speed: float, seed: int) -> Dict[str, Any]:
    """Modify the ComfyUI workflow with input parameters."""
    with open("workflows/vibevoice_tts.json", "r") as f:
        workflow = json.load(f)

    # Update node values
    workflow["nodes"][0]["widgets_values"][0] = text  # Text input
    workflow["nodes"][1]["widgets_values"][0] = ref_audio_path  # Reference audio
    workflow["nodes"][2]["widgets_values"][0] = temperature  # Temperature
    workflow["nodes"][3]["widgets_values"][0] = speed  # Speed
    workflow["nodes"][4]["widgets_values"][0] = seed  # Seed

    return workflow

async def execute_workflow(workflow: Dict[str, Any]) -> str:
    """Execute the workflow via ComfyUI websockets."""
    uri = "ws://localhost:8188/ws"
    try:
        async with websockets.connect(uri) as websocket:
            # Queue the prompt
            prompt_msg = {
                "type": "prompt",
                "data": workflow
            }
            await websocket.send(json.dumps(prompt_msg))

            # Wait for execution to complete
            while True:
                response = await websocket.recv()
                data = json.loads(response)

                if data["type"] == "execution_cached":
                    continue
                elif data["type"] == "execution_success":
                    # Assume output is saved to output/vibevoice_output.wav
                    return "output/vibevoice_output.wav"
                elif data["type"] == "execution_error":
                    raise Exception(f"ComfyUI execution error: {data['data']['message']}")
    except Exception as e:
        raise Exception(f"WebSocket error: {str(e)}")

def get_audio_output(audio_path: str, seed: int) -> Dict[str, Any]:
    """Get audio output as base64 with metadata."""
    try:
        import torchaudio
        waveform, sample_rate = torchaudio.load(audio_path)
        duration = waveform.shape[1] / sample_rate

        with open(audio_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode()

        return {
            "audio_base64": audio_b64,
            "duration": duration,
            "sample_rate": sample_rate,
            "seed_used": seed
        }
    except Exception as e:
        raise Exception(f"Error processing audio output: {str(e)}")

def handler(event):
    """
    Main handler function for RunPod requests.
    """
    temp_files = []
    try:
        # Validate input
        input_data = event.get("input", {})
        request = TTSRequest(**input_data)

        # Process reference audio
        ref_audio_path = process_reference_audio(request.reference_audio)
        if ref_audio_path.startswith("/tmp"):  # Temp file
            temp_files.append(ref_audio_path)

        # Modify workflow
        workflow = modify_workflow(
            request.text,
            ref_audio_path,
            request.temperature,
            request.speed,
            request.seed
        )

        # Execute workflow
        audio_path = asyncio.run(execute_workflow(workflow))

        # Get output
        output = get_audio_output(audio_path, request.seed)

        return output

    except Exception as e:
        return {"error": str(e)}
    finally:
        # Cleanup temp files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass

if __name__ == "__main__":
    # Test handler
    test_event = {
        "input": {
            "text": "Hello, this is a test.",
            "temperature": 0.9,
            "speed": 1.2,
            "seed": 123
        }
    }
    result = handler(test_event)
    print("Test result:", result)