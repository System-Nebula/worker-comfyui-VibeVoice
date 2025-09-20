# Multi-stage Dockerfile for RunPod worker with ComfyUI-VibeVoice
# Stage 1: Base setup and dependencies
FROM runpod/worker-comfyui:latest as base

# Requires CUDA-compatible GPU with minimum 10GB VRAM

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    git-lfs \
    && rm -rf /var/lib/apt/lists/*

# Install ComfyUI-VibeVoice custom nodes
RUN comfy node install --mode=remote ComfyUI-VibeVoice

# Stage 2: Model pre-baking
FROM base as model-stage

# Set working directory to ComfyUI root
WORKDIR /workspace/ComfyUI

# Pre-download and bake VibeVoice-Large model
RUN python3 -c "\
import os; \
from huggingface_hub import snapshot_download; \
cache_dir = '/workspace/ComfyUI/models/tts/VibeVoice'; \
os.makedirs(cache_dir, exist_ok=True); \
print('Downloading VibeVoice-Large model...'); \
snapshot_download(repo_id='aoi-ot/VibeVoice-Large', local_dir=os.path.join(cache_dir, 'VibeVoice-Large'), local_dir_use_symlinks=False); \
print('VibeVoice-Large model downloaded successfully') \
"

# Stage 3: Final image
FROM base

# Copy pre-baked models from model-stage
COPY --from=model-stage /workspace/ComfyUI/models/tts/VibeVoice /workspace/ComfyUI/models/tts/VibeVoice

# Copy default reference audio file
COPY input/Kirk_BSidesSeattle[2cx1K6z7YTQ].wav /workspace/ComfyUI/input/maya.wav

# Set working directory
WORKDIR /workspace/ComfyUI

# Configure environment variables
ENV MODEL_PATH=/workspace/ComfyUI/models/tts/VibeVoice
ENV HF_TOKEN=${HF_TOKEN}
ENV CUDA_VISIBLE_DEVICES=0
ENV TORCH_USE_CUDA_DSA=1

# Ensure proper permissions
RUN chmod -R 755 /workspace/ComfyUI/models/tts/VibeVoice

# Expose port if needed (ComfyUI typically runs on 8188)
EXPOSE 8188

# Default command (RunPod will override)
CMD ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188"]