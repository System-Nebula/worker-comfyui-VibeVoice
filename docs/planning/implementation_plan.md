# TTS RunPod Worker: Complete Implementation Plan

## Project Mission
Deploy a production-ready RunPod Serverless worker that converts text + reference audio into expressive speech using ComfyUI + VibeVoice-Large. Target: <30s cold start, <10s generation, base64 WAV output for seamless API integration.

## Architecture Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Runtime** | RunPod Serverless | Auto-scaling GPU inference |
| **Framework** | ComfyUI + Custom Nodes | Visual workflow orchestration |
| **Model** | VibeVoice-Large (9.34B) | Zero-shot voice cloning TTS |
| **API** | RunPod Handler → ComfyUI | Input processing → workflow execution |
| **Storage** | Base64 encoding | Audio I/O without file persistence |

## Core Data Flow

```
Client POST → RunPod API → Handler (rp_handler.py)
  ↓
[Input Processing] → Base64 decode / URL download / maya.wav fallback
  ↓
[Workflow Override] → Load vibevoice_tts.json → Inject text/ref/params
  ↓
[ComfyUI Execution] → /prompt API → Poll /history → Generate WAV
  ↓
[Output Processing] → Encode WAV → Return base64 + metadata
  ↓
Client receives: {"audio_b64": "...", "duration": 3.2s, "seed": 42}
```

## File Structure & Contents

```
tts-vibevvoice-worker/
├── Dockerfile                    # Pre-baked model + custom nodes
├── rp_handler.py                 # Core API logic (400 LOC)
├── requirements.txt              # Audio processing deps
├── workflows/
│   └── vibevoice_tts.json        # ComfyUI workflow (5 nodes)
├── input/
│   └── maya.wav                  # Default 3s female reference
├── test/
│   ├── test_inputs.json          # 4 test cases
│   └── run_tests.py              # Local Docker validation
├── deploy/
│   ├── build.sh                  # Docker build + push
│   └── runpod-template.json      # Endpoint config
├── docs/
│   └── API.md                    # Input/output spec + cURL examples
└── README.md                     # One-command deployment
```

## Phase 1: Foundation (2 hours)

### 1.1 Repository Bootstrap
```bash
# Clone and structure
git clone https://github.com/runpod-workers/worker-comfyui.git tts-vibevvoice-worker
cd tts-vibevvoice-worker

# Create directories
mkdir -p workflows input test deploy docs

# Initialize files
touch requirements.txt rp_handler.py .gitignore README.md

# Git setup
git checkout -b main
git add . && git commit -m "Initial TTS worker structure"
```

### 1.2 Default Reference Audio
```bash
# Download neutral female voice sample (3s, 24kHz)
curl -L -o input/maya.wav \
  "https://github.com/coqui-ai/TTS/raw/main/samples/ljspeech/wav/LJ001-0009.wav"

# Verify
ffprobe input/maya.wav  # Should show ~3s duration, mono, 22050Hz
```

### 1.3 Gitignore Configuration
```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
virtualenv/
.venv/

# Audio files
*.wav
*.mp3
*.flac
input/maya.wav  # Keep in repo, ignore local copies

# Docker
Dockerfile.*
docker-compose.*

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
```

## Phase 2: Docker Foundation (3 hours)

### 2.1 Optimized Dockerfile
```dockerfile
# Use stable base with CUDA 12.1 + PyTorch 2.3
FROM runpod/worker-comfyui:stable-cuda

# Switch to root for system packages
USER root

# Install audio/system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    git-lfs \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Enable Git LFS for large model files
RUN git lfs install

# Hugging Face authentication (build-time)
ARG HUGGINGFACE_TOKEN
ENV HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN}
ENV HF_HOME=/root/.cache/huggingface
ENV TRANSFORMERS_CACHE=/root/.cache/huggingface/transformers

# Install VibeVoice custom nodes
WORKDIR /workspace/ComfyUI/custom_nodes
RUN git clone --depth 1 https://github.com/wildminder/ComfyUI-VibeVoice.git \
    && cd ComfyUI-VibeVoice \
    && pip install -e .

# Install Python dependencies
WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download VibeVoice-Large (critical for cold start performance)
RUN python -c "
import os
from huggingface_hub import snapshot_download
os.environ['HF_TOKEN'] = '${HUGGINGFACE_TOKEN}'
print('Downloading VibeVoice-Large...')
snapshot_download(
    repo_id='aoi-ot/VibeVoice-Large',
    cache_dir='/root/.cache/huggingface/hub',
    local_dir='/workspace/ComfyUI/models/tts/vibevvoice-large',
    local_dir_use_symlinks=False,
    ignore_patterns=['*.gitattributes']
)
print('Model download complete')
"

# Copy application files
COPY workflows/ /workspace/workflows/
COPY input/maya.wav /workspace/comfyui/input/
COPY rp_handler.py /workspace/
COPY deploy/runpod-template.json /workspace/

# Create runtime directories
RUN mkdir -p /workspace/comfyui/{input,output} \
    && chmod -R 755 /workspace/comfyui

# Configure environment
ENV COMFYUI_INPUT_DIR=/workspace/comfyui/input \
    COMFYUI_OUTPUT_DIR=/workspace/comfyui/output \
    COMFYUI_API_PORT=8188 \
    PYTHONPATH=/workspace \
    CUDA_VISIBLE_DEVICES=0

# Switch back to non-root user
USER 1000:1000

# Expose ComfyUI port (optional, for local debugging)
EXPOSE 8188

WORKDIR /workspace
```

### 2.2 Requirements Specification
```txt
# Core RunPod integration
runpod==1.0.5

# HTTP and file handling
requests==2.31.0
aiohttp==3.9.1

# Audio processing
soundfile==0.12.1
librosa==0.10.1
pydub==0.25.1
torch-audiomentations==0.12.0

# Data processing
numpy==1.24.3
Pillow==10.0.1

# Utilities
python-multipart==0.0.6
python-dotenv==1.0.0
```

## Phase 3: ComfyUI Workflow (2 hours)

### 3.1 VibeVoice Workflow JSON
Create `workflows/vibevoice_tts.json`:

```json
{
  "last_node_id": 6,
  "last_link_id": 5,
  "nodes": [
    {
      "id": 1,
      "type": "LoadAudio",
      "title": "Reference Audio Loader",
      "pos": [50, 100],
      "size": {"0": 200, "1": 82},
      "flags": {},
      "order": 0,
      "mode": 0,
      "outputs": [
        {
          "name": "AUDIO",
          "type": "AUDIO",
          "links": [1],
          "shape": 3,
          "slot_index": 0
        }
      ],
      "properties": {"Node name for S&R": "LoadAudio"},
      "widgets_values": ["__REFERENCE_PATH__"]
    },
    {
      "id": 2,
      "type": "VibeVoice_TTS",
      "title": "VibeVoice Speech Synthesis",
      "pos": [300, 100],
      "size": {"0": 315, "1": 400},
      "flags": {},
      "order": 1,
      "mode": 0,
      "inputs": [
        {
          "name": "reference_audio",
          "type": "AUDIO",
          "link": 1,
          "link_id": 1
        }
      ],
      "outputs": [
        {
          "name": "AUDIO",
          "type": "AUDIO",
          "links": [2],
          "shape": 3,
          "slot_index": 0
        }
      ],
      "properties": {
        "Node name for S&R": "VibeVoice_TTS",
        "model_repo": "aoi-ot/VibeVoice-Large"
      },
      "widgets_values": [
        "__TEXT_INPUT__",           // 0: text prompt
        42,                         // 1: seed
        0.7,                        // 2: temperature
        1.0,                        // 3: speed
        1.0,                        // 4: voice_strength
        "cuda",                     // 5: device
        "float16",                  // 6: dtype
        20,                         // 7: diffusion_steps
        1.3,                        // 8: cfg_scale
        "flash_attention_2"         // 9: attention_mode
      ]
    },
    {
      "id": 3,
      "type": "SaveAudio",
      "title": "WAV Output",
      "pos": [650, 100],
      "size": {"0": 200, "1": 82},
      "flags": {},
      "order": 2,
      "mode": 0,
      "inputs": [
        {
          "name": "audio",
          "type": "AUDIO",
          "link": 2,
          "link_id": 2
        },
        {
          "name": "basename",
          "type": "STRING",
          "link": null
        }
      ],
      "properties": {"Node name for S&R": "SaveAudio"},
      "widgets_values": ["__OUTPUT_BASENAME__", 24000]
    },
    {
      "id": 4,
      "type": "PrimitiveNode",
      "title": "Seed Generator",
      "pos": [300, 550],
      "size": {"0": 315, "1": 58},
      "flags": {},
      "order": 3,
      "mode": 0,
      "outputs": [
        {
          "name": "INT",
          "type": "INT",
          "links": null,
          "slot_index": 0
        }
      ],
      "properties": {"Node name for S&R": "PrimitiveNode"},
      "widgets_values": [42]
    },
    {
      "id": 5,
      "type": "Note",
      "title": "Workflow Notes",
      "pos": [50, 550],
      "size": {"0": 900, "1": 100},
      "flags": {},
      "order": 4,
      "mode": 0,
      "properties": {"text_color": "0.47843137254901963,0.8392156862745098,0.8313725490196079"},
      "widgets_values": [
        "VibeVoice TTS Pipeline\n\nInputs:\n• __REFERENCE_PATH__: Audio file path\n• __TEXT_INPUT__: Speech text\n• __OUTPUT_BASENAME__: Output filename\n\nSettings:\n• Temperature: 0.7 (creativity)\n• Speed: 1.0x\n• CFG Scale: 1.3 (guidance)\n• 24kHz output"
      ]
    }
  ],
  "links": [
    [1, 1, 0, 2, 0, 0, "AUDIO"],
    [2, 2, 0, 3, 0, 0, "AUDIO"]
  ],
  "groups": [],
  "config": {},
  "extra": {},
  "version": 0.4
}
```

### 3.2 Node Override Strategy
The handler will replace these placeholders during execution:
- `__REFERENCE_PATH__` → `/workspace/comfyui/input/ref_abc123.wav`
- `__TEXT_INPUT__` → Client-provided text (sanitized)
- `__OUTPUT_BASENAME__` → `tts_job123_abc`

## Phase 4: RunPod Handler Core (4 hours)

### 4.1 Complete Handler Implementation
Create `rp_handler.py`:

```python
#!/usr/bin/env python3
'''
RunPod Serverless Handler for VibeVoice TTS
Accepts: text + optional reference audio (base64/URL)
Returns: base64-encoded WAV + generation metadata
'''

import os
import re
import json
import time
import uuid
import base64
import pathlib
import tempfile
import logging
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse
import runpod
from runpod.serverless import Handler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
COMFY_HOST = "http://127.0.0.1:8188"
INPUT_DIR = pathlib.Path("/workspace/comfyui/input")
OUTPUT_DIR = pathlib.Path("/workspace/comfyui/output")
WORKFLOW_PATH = pathlib.Path("/workspace/workflows/vibevoice_tts.json")
DEFAULT_REF = INPUT_DIR / "maya.wav"
MAX_TEXT_LENGTH = 500
MAX_AUDIO_SIZE_MB = 10

class AudioProcessor:
    '''Handle audio input validation and processing'''
    
    @staticmethod
    def is_valid_wav_header(data: bytes) -> bool:
        '''Basic WAV header validation'''
        if len(data) < 44:  # Minimum WAV header size
            return False
        return data[:4] == b'RIFF' and data[8:12] == b'WAVE'
    
    @staticmethod
    def validate_base64_audio(b64_data: str) -> Tuple[bool, str]:
        '''Validate base64 audio input'''
        try:
            # Decode and check size
            audio_bytes = base64.b64decode(b64_data)
            if len(audio_bytes) > MAX_AUDIO_SIZE_MB * 1024 * 1024:
                return False, f"Audio too large: {len(audio_bytes)/1024/1024:.1f}MB"
            
            # Validate WAV format
            if not AudioProcessor.is_valid_wav_header(audio_bytes):
                return False, "Invalid WAV format"
            
            return True, "Valid"
        except Exception as e:
            return False, f"Decode error: {str(e)}"
    
    @staticmethod
    def save_b64_audio(b64_data: str, output_path: pathlib.Path) -> pathlib.Path:
        '''Save base64 audio to file'''
        audio_bytes = base64.b64decode(b64_data)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(audio_bytes)
        return output_path
    
    @staticmethod
    def download_url_audio(url: str, output_path: pathlib.Path, timeout: int = 30) -> Optional[pathlib.Path]:
        '''Download audio from URL'''
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                return None
            
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Validate downloaded file
            if output_path.stat().st_size > MAX_AUDIO_SIZE_MB * 1024 * 1024:
                output_path.unlink()
                return None
            
            return output_path
        except Exception as e:
            logger.error(f"URL download failed: {e}")
            if output_path.exists():
                output_path.unlink()
            return None
    
    @staticmethod
    def get_reference_path(ref_b64: Optional[str], ref_url: Optional[str]) -> Tuple[Optional[pathlib.Path], str]:
        '''Get reference audio path with fallback logic'''
        # Try base64 first
        if ref_b64:
            is_valid, message = AudioProcessor.validate_base64_audio(ref_b64)
            if is_valid:
                temp_path = INPUT_DIR / f"ref_b64_{uuid.uuid4().hex[:8]}.wav"
                AudioProcessor.save_b64_audio(ref_b64, temp_path)
                return temp_path, f"Using base64 reference ({temp_path.name})"
        
        # Try URL second
        if ref_url:
            temp_path = INPUT_DIR / f"ref_url_{uuid.uuid4().hex[:8]}.wav"
            result = AudioProcessor.download_url_audio(ref_url, temp_path)
            if result:
                return result, f"Using URL reference ({result.name})"
        
        # Fallback to default
        if DEFAULT_REF.exists():
            return DEFAULT_REF, "Using default maya.wav reference"
        
        return None, "No valid reference audio available"

class ComfyAPIClient:
    '''ComfyUI API interaction layer'''
    
    @staticmethod
    def submit_workflow(workflow: Dict[str, Any]) -> str:
        '''Submit workflow to ComfyUI /prompt endpoint'''
        try:
            payload = {"workflow": workflow}
            response = requests.post(
                f"{COMFY_HOST}/prompt",
                json=payload,
                timeout=60,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            prompt_id = response.json().get("prompt_id")
            if not prompt_id:
                raise ValueError("No prompt_id returned from ComfyUI")
            return prompt_id
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"ComfyUI submission failed: {e}")
    
    @staticmethod
    def poll_completion(prompt_id: str, timeout_seconds: int = 600) -> Dict[str, Any]:
        '''Poll /history until completion or timeout'''
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            try:
                response = requests.get(
                    f"{COMFY_HOST}/history/{prompt_id}",
                    timeout=30
                )
                response.raise_for_status()
                history = response.json()
                
                if prompt_id in history:
                    prompt_data = history[prompt_id]
                    if prompt_data.get("outputs"):
                        return prompt_data
                
                time.sleep(2)
            except requests.exceptions.RequestException as e:
                logger.warning(f"History poll error: {e}")
                time.sleep(5)
        
        raise TimeoutError(f"ComfyUI prompt {prompt_id} timed out after {timeout_seconds}s")

class WorkflowManager:
    '''Handle workflow loading and parameter injection'''
    
    PLACEHOLDERS = {
        '__REFERENCE_PATH__': None,
        '__TEXT_INPUT__': None,
        '__OUTPUT_BASENAME__': None
    }
    
    @staticmethod
    def load_base_workflow() -> Dict[str, Any]:
        '''Load and validate workflow JSON'''
        if not WORKFLOW_PATH.exists():
            raise FileNotFoundError(f"Workflow not found: {WORKFLOW_PATH}")
        
        with open(WORKFLOW_PATH, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        
        # Basic validation
        if 'nodes' not in workflow or len(workflow['nodes']) < 3:
            raise ValueError("Invalid workflow structure")
        
        return workflow
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        '''Clean and truncate input text'''
        # Remove control characters, limit length
        cleaned = re.sub(r'[\x00-\x1F\x7F]', '', text)
        return cleaned[:MAX_TEXT_LENGTH].strip()
    
    @staticmethod
    def inject_parameters(
        workflow: Dict[str, Any],
        text: str,
        ref_path: pathlib.Path,
        basename: str,
        seed: int,
        temperature: float,
        speed: float
    ) -> Dict[str, Any]:
        '''Replace placeholders and update node parameters'''
        
        # Sanitize inputs
        clean_text = WorkflowManager.sanitize_text(text)
        basename = re.sub(r'[^\w\-_.]', '_', basename)[:50]
        
        # Update node widgets_values
        for node in workflow['nodes']:
            if node['type'] == 'LoadAudio' and node['id'] == 1:
                if 'widgets_values' in node and len(node['widgets_values']) > 0:
                    node['widgets_values'][0] = str(ref_path)
            
            elif node['type'] == 'VibeVoice_TTS' and node['id'] == 2:
                if 'widgets_values' in node and len(node['widgets_values']) >= 10:
                    widgets = node['widgets_values']
                    widgets[0] = clean_text           # text
                    widgets[1] = seed                 # seed
                    widgets[2] = max(0.1, min(2.0, temperature))  # temperature
                    widgets[3] = max(0.5, min(2.0, speed))        # speed
                    widgets[7] = 20                   # diffusion_steps
                    widgets[8] = 1.3                  # cfg_scale
            
            elif node['type'] == 'SaveAudio' and node['id'] == 3:
                if 'widgets_values' in node and len(node['widgets_values']) >= 2:
                    node['widgets_values'][0] = basename  # basename
                    node['widgets_values'][1] = 24000     # sample_rate
            
            # Update seed primitive
            elif node['type'] == 'PrimitiveNode':
                if 'widgets_values' in node:
                    node['widgets_values'][0] = seed
        
        logger.info(f"Injected parameters: text_len={len(clean_text)}, seed={seed}")
        return workflow

def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    '''
    Main RunPod serverless handler
    
    Input schema:
    {
        "text": "Hello world",
        "reference_audio": "base64_wav_data",  # optional
        "reference_audio_url": "https://...",  # optional  
        "voice_settings": {
            "temperature": 0.7,  # 0.1-2.0
            "speed": 1.0         # 0.5-2.0
        }
    }
    
    Output schema:
    {
        "success": true,
        "audio_b64": "base64_wav_data",
        "duration_seconds": 3.2,
        "seed_used": 42,
        "prompt_id": "prompt_123",
        "reference_used": "maya.wav"
    }
    '''
    
    job_id = job.get('id', str(uuid.uuid4()))
    start_time = time.time()
    
    try:
        # Parse and validate input
        input_data = job.get('input', {})
        text = input_data.get('text', '').strip()
        
        if not text or len(text.strip()) == 0:
            return {
                'error': 'Text input is required',
                'delay_time': 1,
                'metrics': {'execution_time': time.time() - start_time}
            }
        
        # Extract audio reference
        ref_b64 = input_data.get('reference_audio')
        ref_url = input_data.get('reference_audio_url')
        
        # Get reference audio path
        ref_path, ref_info = AudioProcessor.get_reference_path(ref_b64, ref_url)
        if not ref_path:
            return {
                'error': ref_info,
                'delay_time': 2,
                'metrics': {'execution_time': time.time() - start_time}
            }
        
        # Extract voice settings with defaults
        settings = input_data.get('voice_settings', {})
        temperature = float(settings.get('temperature', 0.7))
        speed = float(settings.get('speed', 1.0))
        
        # Generate identifiers
        basename = f"tts_{job_id[:8]}"
        seed = int((time.time() * 1000 + uuid.uuid4().int % 1000) % (2**32))
        
        logger.info(f"Starting job {job_id}: '{text[:50]}...', ref={ref_info}")
        
        # Load and modify workflow
        workflow = WorkflowManager.load_base_workflow()
        modified_workflow = WorkflowManager.inject_parameters(
            workflow, text, ref_path, basename, seed, temperature, speed
        )
        
        # Submit to ComfyUI
        prompt_id = ComfyAPIClient.submit_workflow(modified_workflow)
        logger.info(f"Submitted to ComfyUI: prompt_id={prompt_id}")
        
        # Wait for completion
        history = ComfyAPIClient.poll_completion(prompt_id)
        
        # Locate output file
        output_pattern = OUTPUT_DIR / f"{basename}*.wav"
        output_files = list(output_pattern.glob('*.wav'))
        
        if not output_files:
            raise RuntimeError(f"No output WAV generated for {basename}")
        
        output_file = output_files[0]
        logger.info(f"Generated: {output_file}")
        
        # Read and encode output
        with open(output_file, 'rb') as f:
            audio_data = f.read()
        
        # Calculate duration estimate (24kHz, 16-bit stereo = 4 bytes/sample)
        estimated_samples = len(audio_data) // 4
        duration_seconds = estimated_samples / 24000.0
        
        # Cleanup temporary files
        if ref_path != DEFAULT_REF and ref_path.exists():
            ref_path.unlink()
        if output_file.exists():
            output_file.unlink()
        
        execution_time = time.time() - start_time
        
        logger.info(f"Job {job_id} completed in {execution_time:.2f}s")
        
        return {
            'success': True,
            'prompt_id': prompt_id,
            'audio_b64': base64.b64encode(audio_data).decode('utf-8'),
            'duration_seconds': round(duration_seconds, 2),
            'seed_used': seed,
            'reference_used': ref_info,
            'text_length': len(text),
            'metrics': {
                'execution_time': round(execution_time, 2),
                'model': 'VibeVoice-Large',
                'sample_rate': 24000
            }
        }
    
    except TimeoutError as e:
        logger.error(f"Job {job_id} timed out: {e}")
        return {
            'error': f'Generation timeout: {str(e)}',
            'delay_time': 5,
            'metrics': {'execution_time': time.time() - start_time}
        }
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        return {
            'error': f'Processing failed: {str(e)}',
            'delay_time': 2,
            'metrics': {'execution_time': time.time() - start_time}
        }

# RunPod serverless entrypoint
if __name__ == '__main__':
    runpod.serverless.start({'handler': handler})
```

## Phase 5: Testing Framework (2 hours)

### 5.1 Test Cases Definition
Create `test/test_inputs.json`:

```json
[
  {
    "name": "Basic text generation",
    "description": "Simple text with default voice",
    "input": {
      "text": "Hello, this is a test of the VibeVoice TTS system running on RunPod.",
      "voice_settings": {
        "temperature": 0.7,
        "speed": 1.0
      }
    },
    "expected": {
      "success": true,
      "audio_b64": {"type": "string", "minLength": 5000},
      "duration_seconds": {"min": 2.0, "max": 5.0},
      "reference_used": "Using default maya.wav reference"
    }
  },
  {
    "name": "Custom reference audio",
    "description": "Base64 encoded reference voice",
    "input": {
      "text": "This message uses a custom reference voice for synthesis.",
      "reference_audio": "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMc=",
      "voice_settings": {
        "temperature": 0.9,
        "speed": 0.8
      }
    },
    "expected": {
      "success": true,
      "reference_used": {"pattern": "Using base64 reference"}
    }
  },
  {
    "name": "URL reference audio",
    "description": "Download reference from external URL",
    "input": {
      "text": "Testing URL-based reference audio download capability.",
      "reference_audio_url": "https://github.com/coqui-ai/TTS/raw/main/samples/ljspeech/wav/LJ001-0009.wav",
      "voice_settings": {
        "temperature": 0.6,
        "speed": 1.2
      }
    },
    "expected": {
      "success": true,
      "reference_used": {"pattern": "Using URL reference"}
    }
  },
  {
    "name": "Long text truncation",
    "description": "Test text length limiting and sanitization",
    "input": {
      "text": "This is a very long text input that exceeds the maximum allowed length of five hundred characters and contains special characters like @#$% that need to be sanitized for safe processing through the TTS pipeline. The system should truncate this intelligently while preserving meaning.",
      "voice_settings": {
        "temperature": 0.8,
        "speed": 1.0
      }
    },
    "expected": {
      "success": true,
      "text_length": 500,
      "reference_used": "Using default maya.wav reference"
    }
  },
  {
    "name": "Invalid input handling",
    "description": "Test error conditions gracefully",
    "input": {
      "text": "",
      "reference_audio": "invalid_base64_data_not_wav_format",
      "voice_settings": {
        "temperature": 999  # Invalid value
      }
    },
    "expected": {
      "error": true,
      "delay_time": {"min": 1, "max": 5}
    }
  }
]
```

### 5.2 Automated Test Runner
Create `test/run_tests.py`:

```python
#!/usr/bin/env python3
'''
Local testing framework for TTS worker
Supports Docker build testing and handler unit tests
'''

import json
import subprocess
import tempfile
import os
import sys
import time
from pathlib import Path
import pytest

# Test configuration
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent
DOCKER_IMAGE = "tts-vibevvoice-worker:test"

class TestTTSWorker:
    '''Main test suite'''
    
    @pytest.fixture(scope="session")
    def docker_image(self):
        '''Build Docker image if not present'''
        if not self._image_exists():
            print("🔨 Building Docker image...")
            result = subprocess.run([
                "docker", "build",
                "--build-arg", "HUGGINGFACE_TOKEN=dummy_token_for_test",
                "-t", DOCKER_IMAGE, "."
            ], cwd=PROJECT_ROOT, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Docker build failed:\n{result.stderr}")
                pytest.skip("Docker build failed")
        
        return DOCKER_IMAGE
    
    def _image_exists(self):
        '''Check if test Docker image exists'''
        result = subprocess.run(["docker", "images", "-q", DOCKER_IMAGE], 
                              capture_output=True)
        return result.returncode == 0 and result.stdout.strip()
    
    def test_handler_basic(self):
        '''Test handler with basic input'''
        from rp_handler import handler
        
        test_input = {
            "input": {
                "text": "Hello test",
                "voice_settings": {"temperature": 0.7}
            },
            "id": "test-123"
        }
        
        result = handler(test_input)
        
        assert result.get('success') is True, f"Expected success, got: {result}"
        assert 'audio_b64' in result, "Missing audio output"
        assert len(result['audio_b64']) > 1000, "Audio too short"
        assert result['text_length'] == len("Hello test")
    
    def test_docker_local_run(self, docker_image):
        '''Test complete Docker execution'''
        with tempfile.TemporaryDirectory() as temp_dir:
            # Prepare test job
            test_job = {
                "input": {
                    "text": "Docker test message",
                    "voice_settings": {"temperature": 0.7, "speed": 1.0}
                }
            }
            
            # Run container
            cmd = [
                "docker", "run", "--rm", "-i",
                f"-v{temp_dir}:/workspace/comfyui/output",
                "-e", "HUGGINGFACE_TOKEN=dummy",
                "--network", "host",  # For ComfyUI localhost access
                docker_image,
                "--job", json.dumps(test_job)
            ]
            
            print(f"🚀 Running: {' '.join(cmd[:3])}...")
            result = subprocess.run(
                cmd, 
                input=json.dumps(test_job),
                capture_output=True, 
                text=True,
                timeout=300
            )
            
            print(f"Container logs:\n{result.stdout}")
            if result.stderr:
                print(f"Container errors:\n{result.stderr}")
            
            assert result.returncode == 0, "Docker run failed"
            assert json.loads(result.stdout).get('success') is True
    
    def test_workflow_validation(self):
        '''Validate workflow JSON structure'''
        workflow_path = PROJECT_ROOT / "workflows" / "vibevoice_tts.json"
        
        with open(workflow_path, 'r') as f:
            workflow = json.load(f)
        
        # Check required structure
        assert 'nodes' in workflow
        assert len(workflow['nodes']) >= 3
        
        # Verify key nodes exist
        node_types = [node.get('type') for node in workflow['nodes']]
        assert 'LoadAudio' in node_types
        assert 'VibeVoice_TTS' in node_types
        assert 'SaveAudio' in node_types
    
    def test_audio_processor(self):
        '''Test audio processing utilities'''
        from rp_handler import AudioProcessor
        
        # Test invalid base64
        valid, msg = AudioProcessor.validate_base64_audio("invalid_base64")
        assert not valid
        
        # Test default reference exists
        default_path = PROJECT_ROOT / "input" / "maya.wav"
        assert default_path.exists(), "Default reference audio missing"

if __name__ == "__main__":
    # Run pytest if available, otherwise basic test
    try:
        import pytest
        sys.exit(pytest.main([__file__, "-v"]))
    except ImportError:
        # Fallback to basic testing
        tester = TestTTSWorker()
        tester.test_handler_basic()
        tester.test_workflow_validation()
        print("✅ Basic tests passed")
```

### 5.3 Performance Benchmarks
```bash
# Performance testing script
python test/benchmark.py

# Expected results:
# Cold start: <30s (first run)
# Warm generation: <10s for 100 words
# Memory usage: <8GB VRAM peak
```

## Phase 6: Deployment Automation (1 hour)

### 6.1 Build & Deploy Script
Create `deploy/build.sh`:

```bash
#!/bin/bash
set -euo pipefail

# Configuration
HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN:-""}
IMAGE_NAME="ghcr.io/${GITHUB_USERNAME}/tts-vibevvoice-worker"
TAG="latest"
REGISTRY="ghcr.io"

# Validate prerequisites
if [[ -z "$HUGGINGFACE_TOKEN" ]]; then
    echo "❌ Set HUGGINGFACE_TOKEN environment variable"
    exit 1
fi

if [[ -z "$GITHUB_USERNAME" ]]; then
    echo "❌ Set GITHUB_USERNAME environment variable"
    exit 1
fi

# Login to registry
echo "🔐 Logging into $REGISTRY..."
echo $HUGGINGFACE_TOKEN | docker login $REGISTRY -u $GITHUB_USERNAME --password-stdin

# Build image
echo "🔨 Building Docker image..."
docker build \
    --platform linux/amd64 \
    --build-arg HUGGINGFACE_TOKEN="$HUGGINGFACE_TOKEN" \
    --progress=plain \
    -t $IMAGE_NAME:$TAG \
    -t $IMAGE_NAME:serverless \
    .

# Test local build
echo "🧪 Testing local build..."
docker run --rm --platform linux/amd64 \
    -e HUGGINGFACE_TOKEN="$HUGGINGFACE_TOKEN" \
    $IMAGE_NAME:$TAG \
    python -c "
import sys
print('✅ Python environment OK')
from runpod.serverless import start
print('✅ RunPod integration OK')
import torch
print(f'✅ PyTorch {torch.__version__} CUDA {torch.cuda.is_available()}')
"

# Push to registry
echo "📤 Pushing to registry..."
docker push $IMAGE_NAME:$TAG
docker push $IMAGE_NAME:serverless

echo "🎉 Deployment complete!"
echo "Image: $IMAGE_NAME:$TAG"
echo ""
echo "Next: Create RunPod endpoint with:"
echo "  Image: $IMAGE_NAME:$TAG"
echo "  GPU: NVIDIA RTX A6000 (48GB) or A40 (48GB)"
echo "  Memory: 50GB container disk"
```

### 6.2 RunPod Endpoint Template
Create `deploy/runpod-template.json`:

```json
{
  "name": "VibeVoice TTS Worker",
  "imageName": "ghcr.io/YOUR_USERNAME/tts-vibevvoice-worker:latest",
  "containerDiskInGb": 50,
  "volumeInGb": 20,
  "volumeMountPath": "/workspace/comfyui/output",
  "env": [
    {
      "key": "HUGGINGFACE_TOKEN",
      "value": "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    },
    {
      "key": "COMFYUI_INPUT_DIR",
      "value": "/workspace/comfyui/input"
    },
    {
      "key": "COMFYUI_OUTPUT_DIR", 
      "value": "/workspace/comfyui/output"
    },
    {
      "key": "MAX_CONCURRENT_JOBS",
      "value": "2"
    }
  ],
  "templateType": "ServerlessWorker",
  "gpuTypeId": "NVIDIA RTX A6000",
  "minWorkers": 0,
  "maxWorkers": 5,
  "idleTimeout": 1800,
  "activeTimeout": 1800,
  "networkVolumeInGb": null
}
```

## Phase 7: API Client & Documentation (1 hour)

### 7.1 Python API Client
Create `client/tts_client.py`:

```python
#!/usr/bin/env python3
'''
VibeVoice TTS Client for RunPod Serverless
'''

import requests
import json
import base64
import time
import os
from typing import Optional, Dict, Any
from pathlib import Path

class VibeVoiceClient:
    '''Client for VibeVoice TTS RunPod worker'''
    
    def __init__(self, api_key: str, endpoint_id: str):
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.base_url = f"https://api.runpod.ai/v2/{endpoint_id}"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def _submit_job(self, input_data: Dict[str, Any]) -> str:
        '''Submit job and return job ID'''
        payload = {"input": input_data}
        
        response = requests.post(f"{self.base_url}/run", 
                               headers=self.headers, 
                               json=payload)
        response.raise_for_status()
        
        return response.json()["id"]
    
    def _poll_job(self, job_id: str, max_wait: int = 300) -> Dict[str, Any]:
        '''Poll job status until completion'''
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status_url = f"{self.base_url}/status/{job_id}"
            response = requests.get(status_url, headers=self.headers)
            response.raise_for_status()
            
            status_data = response.json()
            state = status_data["status"]["state"]
            
            if state == "COMPLETED":
                return status_data["output"]
            elif state in ["FAILED", "CANCELLED"]:
                raise RuntimeError(f"Job {job_id} failed: {status_data['output']}")
            
            time.sleep(2)
        
        raise TimeoutError(f"Job {job_id} timed out after {max_wait}s")
    
    def generate_speech(
        self,
        text: str,
        reference_audio: Optional[bytes] = None,
        reference_url: Optional[str] = None,
        temperature: float = 0.7,
        speed: float = 1.0,
        max_wait: int = 300
    ) -> Dict[str, Any]:
        '''
        Generate speech from text using VibeVoice
        
        Args:
            text: Text to synthesize
            reference_audio: Optional WAV bytes for voice cloning
            reference_url: Optional URL to WAV file
            temperature: Creativity (0.1-2.0)
            speed: Playback speed (0.5-2.0)
            max_wait: Maximum wait time in seconds
            
        Returns:
            Dict with audio_b64, duration, and metadata
        '''
        
        # Prepare input
        input_data = {
            "text": text,
            "voice_settings": {"temperature": temperature, "speed": speed}
        }
        
        if reference_audio:
            audio_b64 = base64.b64encode(reference_audio).decode('utf-8')
            input_data["reference_audio"] = audio_b64
        elif reference_url:
            input_data["reference_audio_url"] = reference_url
        
        # Submit and wait
        job_id = self._submit_job(input_data)
        print(f"🚀 Job submitted: {job_id}")
        
        result = self._poll_job(job_id, max_wait)
        
        if not result.get('success'):
            raise RuntimeError(f"Generation failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    def save_audio(self, result: Dict[str, Any], filename: Optional[str] = None) -> Path:
        '''Save generated audio to file'''
        if not result.get('success') or 'audio_b64' not in result:
            raise ValueError("Invalid result - no audio data")
        
        audio_b64 = result['audio_b64']
        audio_bytes = base64.b64decode(audio_b64)
        
        if filename is None:
            timestamp = int(time.time())
            filename = f"vibevvoice_{timestamp}.wav"
        
        output_path = Path(filename)
        with open(output_path, 'wb') as f:
            f.write(audio_bytes)
        
        print(f"💾 Saved: {output_path} ({len(audio_bytes)/1024:.1f}KB)")
        return output_path

# Example usage
if __name__ == "__main__":
    # Load from environment
    API_KEY = os.getenv("RUNPOD_API_KEY")
    ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
    
    if not API_KEY or not ENDPOINT_ID:
        print("Set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID environment variables")
        sys.exit(1)
    
    # Initialize client
    client = VibeVoiceClient(API_KEY, ENDPOINT_ID)
    
    # Example 1: Default voice
    print("🎤 Generating with default voice...")
    result1 = client.generate_speech("Hello, this is VibeVoice speaking!")
    audio_file1 = client.save_audio(result1)
    print(f"Duration: {result1['duration_seconds']:.1f}s")
    
    # Example 2: Custom reference (if you have a WAV file)
    # with open("my_voice_sample.wav", "rb") as f:
    #     reference_audio = f.read()
    # result2 = client.generate_speech(
    #     "This uses my custom voice sample!",
    #     reference_audio=reference_audio,
    #     temperature=0.9
    # )
    # client.save_audio(result2, "custom_voice_output.wav")
    
    print("✅ All examples completed!")
```

### 7.2 cURL Examples for Testing
Add to `docs/API.md`:

```markdown
## Quick Start - cURL Examples

### Basic Text-to-Speech (Default Voice)
```bash
curl -X POST "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "text": "Hello from VibeVoice! This is expressive text-to-speech.",
      "voice_settings": {
        "temperature": 0.7,
        "speed": 1.0
      }
    }
  }'
```

### With Custom Reference Audio (Base64)
```bash
# First, encode your WAV file:
# base64 -i reference_voice.wav -o ref.b64

curl -X POST "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "text": "This uses my custom reference voice!",
      "reference_audio": "'$(cat ref.b64)'",
      "voice_settings": {
        "temperature": 0.9,
        "speed": 0.8
      }
    }
  }'
```

### With URL Reference Audio
```bash
curl -X POST "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "text": "Testing URL reference download capability.",
      "reference_audio_url": "https://example.com/voice_sample.wav",
      "voice_settings": {
        "temperature": 0.6,
        "speed": 1.2
      }
    }
  }'
```

### Check Job Status
```bash
cURL -X GET "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/status/JOB_ID" \
  -H "Authorization: Bearer YOUR_API_KEY"
```
```

## Phase 8: Production Monitoring (1 hour)

### 8.1 Metrics Dashboard Setup
Add to handler for production monitoring:

```python
# Enhanced logging with structured metrics
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

log = structlog.get_logger()

# Usage in handler:
def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    job_id = job.get('id', str(uuid.uuid4()))
    
    with log.bind(job_id=job_id, text_length=len(job.get('input', {}).get('text', ''))):
        log.info("job_started")
        
        try:
            # ... existing handler logic ...
            
            log.info("job_completed", 
                    execution_time=execution_time,
                    duration_seconds=duration_seconds,
                    audio_size_bytes=len(audio_data),
                    reference_type=ref_info.split()[1])
            
            return result
            
        except Exception as e:
            log.error("job_failed", error=str(e), error_type=type(e).__name__)
            raise
```


### 8.2 Error Rate Monitoring
Track these key metrics in production:

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Success Rate | >99% | <95% over 1h |
| Cold Start Time | <30s | >60s average |
| Generation Time | <10s | >20s p95 |
| Memory Usage | <8GB | >10GB peak |
| Audio Quality | >95% | Manual review |

## Success Checklist

- [ ] **Cold Start** <30s (pre-baked models eliminate download)
- [ ] **Generation** <10s for 100 words (A6000 GPU)
- [ ] **Audio Quality** Natural, expressive speech matching reference
- [ ] **Input Handling** Base64, URL, default fallback all work
- [ ] **Error Resilience** Graceful handling of timeouts, invalid audio
- [ ] **API Compatibility** Standard RunPod serverless interface
- [ ] **Scalability** 5 concurrent workers without degradation
- [ ] **Monitoring** Structured logs + success metrics

## Launch Sequence

```bash
# 1. Build and push (5-10 min)
chmod +x deploy/build.sh
HUGGINGFACE_TOKEN=hf_xxx GITHUB_USERNAME=yourname ./deploy/build.sh

# 2. Deploy to RunPod (2 min)
# Use runpod-template.json in dashboard or:
curl -X POST https://api.runpod.ai/v2/endpoints \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d @deploy/runpod-template.json

# 3. Test endpoint (30s)
ENDPOINT_ID=xxx123
curl -X POST "https://api.runpod.ai/v2/$ENDPOINT_ID/run" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -d '{"input":{"text":"Launch test complete!"}}'

# 4. Monitor first jobs
curl -X GET "https://api.runpod.ai/v2/$ENDPOINT_ID/logs?jobId=$JOB_ID" \
  -H "Authorization: Bearer $RUNPOD_API_KEY"
```

## Post-Launch Roadmap

### Immediate (Week 1)
- [ ] A/B test default vs custom reference quality
- [ ] Add 3-5 curated reference voices to input/
- [ ] Implement audio post-processing (silence trim, normalization)

### Short-term (Week 2-3)
- [ ] Multi-speaker conversation support (prefix format: "Alice: Hello")
- [ ] SSML-like prosody controls (emphasis, breaks)
- [ ] Batch processing for multiple text segments

### Long-term (Month 2)
- [ ] Voice library management API
- [ ] Real-time streaming synthesis
- [ ] Fine-tuning endpoints for custom voices

This implementation delivers a production-ready TTS service with enterprise-grade error handling, monitoring, and deployment automation. The pre-baked model approach ensures sub-30s cold starts while maintaining VibeVoice's expressive zero-shot capabilities.

**Total Implementation Time: ~16 hours**  
**Expected ROI: 10x faster than local GPU setup, infinite scale**
