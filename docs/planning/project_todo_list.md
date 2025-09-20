# Project Todo List: RunPod ComfyUI + VibeVoice TTS Worker

## Project Overview

**Epic**: Deploy custom RunPod worker with ComfyUI + VibeVoice endpoint for TTS workflows

**Base Repository**: Fork and adapt https://github.com/runpod-workers/worker-comfyui

**Working ComfyUI Workflow**: https://huggingface.co/datasets/landam/comfy-workflows/blob/main/LoadAudio-VibeVoiceSS.json

**Reference Material**: https://bondig.dev/posts/how-to-create-a-runpod-worker/

## Development Tasks & Requirements

### Phase 1: Repository Setup & Architecture

#### 1.1 Fork Base Repository
- **Task**: Fork `runpod-workers/worker-comfyui` repository[1][2]
- **Deliverable**: New repository `runpod-worker-vibevoice/`
- **Priority**: High
- **Dependencies**: None

#### 1.2 Repository Structure Setup
- **Task**: Create project directory structure based on documented layout[1]
- **Directory Structure**:
  ```
  runpod-worker-vibevoice/
  ├─ Dockerfile
  ├─ README.md
  ├─ requirements.txt
  ├─ rp_handler.py                 # custom job handler
  ├─ comfyui/
  │  ├─ models/
  │  │  └─ vibevoice/             # pre-fetched model cache
  │  ├─ input/                    # downloaded reference audio
  │  └─ output/                   # generated WAVs
  ├─ ComfyUI/                     # cloned at build
  │  └─ custom_nodes/
  │     └─ ComfyUI-VibeVoice/
  ├─ workflows/
  │  └─ vibevoice_reference_to_wav.json
  └─ input/                       # default reference audio
     └─ maya.wav                  # default voice reference
  ```
- **Priority**: High
- **Dependencies**: 1.1

#### 1.3 Default Audio Asset Integration
- **Task**: Pre-load "maya.wav" as default voice reference[1]
- **Location**: `/input/maya.wav`
- **Purpose**: Fallback voice when no reference audio provided
- **Priority**: Medium
- **Dependencies**: 1.2

### Phase 2: Docker Configuration & Dependencies

#### 2.1 Custom Dockerfile Development
- **Task**: Create optimized Dockerfile from `runpod/worker-comfyui:latest-cuda` base[3][1]
- **Key Requirements**:
  - Start from official base image: `FROM runpod/worker-comfyui:<version>-base`[3]
  - Install system dependencies: `ffmpeg`, `git`, `git-lfs`[1]
  - Clone ComfyUI-VibeVoice custom nodes[4][1]
  - Use `RUN comfy model download` for model pre-loading
  - Configure environment variables and working directories
- **Model Pre-loading**: Use `comfy model download` commands to bake VibeVoice models into image
- **Priority**: High
- **Dependencies**: 1.2

#### 2.2 Python Requirements Configuration
- **Task**: Define Python dependencies in `requirements.txt`[5][1]
- **Base Dependencies**: 
  ```
  runpod==1.*
  requests
  soundfile
  librosa
  numpy
  torchaudio
  ```
- **Additional Dependencies**: Verify ComfyUI-VibeVoice specific requirements[4]
- **Priority**: High
- **Dependencies**: 2.1

#### 2.3 Custom Node Integration
- **Task**: Install ComfyUI-VibeVoice custom nodes[4][1]
- **Method**: Use `comfy-node-install` command in Dockerfile[3]
- **Command**: `RUN comfy-node-install ComfyUI-VibeVoice`[3]
- **Repository**: https://github.com/wildminder/ComfyUI-VibeVoice[4]
- **Priority**: High
- **Dependencies**: 2.1

### Phase 3: ComfyUI Workflow Development

#### 3.1 Workflow JSON Creation
- **Task**: Create `vibevoice_reference_to_wav.json` workflow file[1]
- **Base Template**: Use existing workflow from HuggingFace dataset
- **Key Nodes Required**:
  - `LoadAudio` node for reference audio input
  - `VibeVoice_TTS` node for text-to-speech processing[4]
  - `SaveAudio` node for WAV output
- **Node Configuration**: Support dynamic parameter overrides[1]
- **Priority**: High
- **Dependencies**: 2.3

#### 3.2 Input Validation & Processing
- **Task**: Implement audio input handling supporting both URLs and file paths[1]
- **Supported Formats**: WAV files primarily, with format conversion capability
- **Reference Audio Requirements**:
  - Accept HTTP/HTTPS URLs
  - Accept RunPod storage paths
  - Handle audio format conversion via FFmpeg
- **Priority**: High
- **Dependencies**: 3.1

#### 3.3 Workflow Parameter Management
- **Task**: Enable dynamic node parameter override system[1]
- **Override Targets**:
  - Node 1: `properties.path` → reference audio path
  - Node 2: `inputs.text` → input text, `inputs.seed` → generation seed
  - Node 3: `inputs.basename` → output filename, `inputs.sample_rate` → output sample rate
- **Priority**: Medium
- **Dependencies**: 3.1

### Phase 4: RunPod Handler Implementation

#### 4.1 Custom Handler Development
- **Task**: Create `rp_handler.py` for RunPod integration[5][1]
- **Core Functions**:
  - Input validation (text, reference_audio, sample_rate, seed, basename)
  - Reference audio download and staging
  - ComfyUI workflow loading and parameter injection
  - ComfyUI API interaction (`/prompt`, `/history` endpoints)
  - Output file management and result return
- **API Integration**: ComfyUI server communication at `http://127.0.0.1:8188`[1]
- **Priority**: High
- **Dependencies**: 3.1, 3.2

#### 4.2 Error Handling & Validation
- **Task**: Implement robust error handling and input validation[1]
- **Validation Requirements**:
  - Required fields: `text`, `reference_audio`
  - Optional fields: `sample_rate` (default: 24000), `seed` (default: 0), `basename` (auto-generated)
  - Audio file accessibility validation
- **Error Scenarios**: Network timeouts, invalid audio formats, ComfyUI processing failures
- **Priority**: Medium
- **Dependencies**: 4.1

#### 4.3 Output Management
- **Task**: Implement output file handling and return formatting[1]
- **Output Structure**:
  ```json
  {
    "prompt_id": "...",
    "wav_paths": ["/workspace/comfyui/output/filename.wav"]
  }
  ```
- **File Management**: Clean up temporary input files after processing
- **Priority**: Medium
- **Dependencies**: 4.1

### Phase 5: Model Management & Optimization

#### 5.1 Model Pre-loading Strategy
- **Task**: Implement model pre-download during Docker build[1]
- **Method**: Use `comfy model download` commands in Dockerfile
- **Target Model**: VibeVoice-Large from `aoi-ot/VibeVoice-Large`[1]
- **Cache Location**: `/root/.cache/huggingface`[1]
- **Build Optimization**: Consider model size impact on image build time
- **Priority**: High
- **Dependencies**: 2.1

#### 5.2 VRAM Optimization
- **Task**: Configure memory-efficient settings for faster worker restarts[1]
- **Optimizations**:
  - Pre-baked models to reduce cold start times
  - Efficient model loading configuration
  - Memory management between job executions
- **Target**: Minimize startup time for serverless deployments
- **Priority**: Medium
- **Dependencies**: 5.1

### Phase 6: Testing & Quality Assurance

#### 6.1 Local Testing Framework
- **Task**: Implement local testing capabilities[5]
- **Test Components**:
  - Handler function testing with `test_input.json`
  - Docker container local execution
  - ComfyUI workflow validation
- **Test Cases**: Various input scenarios, error conditions, output validation
- **Priority**: Medium
- **Dependencies**: 4.1, 4.2

#### 6.2 Integration Testing
- **Task**: Test complete workflow from API input to WAV output
- **Test Scenarios**:
  - Valid reference audio URL with text input
  - Local file path reference audio
  - Missing reference audio handling
  - Various audio formats and sample rates
- **Validation**: Output file quality, format compliance, processing time
- **Priority**: Medium
- **Dependencies**: 6.1

### Phase 7: Deployment & Distribution

#### 7.1 Container Registry Setup
- **Task**: Configure Docker image build and push process[5]
- **Registry Options**: Docker Hub, GitHub Container Registry, or RunPod registry
- **Build Command**: `docker build --platform linux/amd64` for RunPod compatibility[5]
- **Versioning**: Semantic versioning strategy for releases
- **Priority**: Medium
- **Dependencies**: 6.2

#### 7.2 RunPod Template Configuration
- **Task**: Create RunPod serverless endpoint template[1]
- **Template Settings**:
  - Container image URL
  - GPU requirements: ≥10-12GB VRAM recommended[1]
  - Environment variables: `HUGGINGFACE_TOKEN`, directory paths
  - Volume mounting for persistent output storage
- **Documentation**: Deployment guide for end users
- **Priority**: Medium
- **Dependencies**: 7.1

#### 7.3 API Documentation
- **Task**: Create comprehensive API documentation
- **Documentation Components**:
  - Input schema specification
  - Output format examples
  - cURL examples for testing[1]
  - Error codes and troubleshooting guide
- **Format**: Markdown documentation with code examples
- **Priority**: Low
- **Dependencies**: 7.2

### Phase 8: Advanced Features & Optimization

#### 8.1 Audio Format Support Enhancement
- **Task**: Expand supported input audio formats beyond WAV
- **Target Formats**: MP3, FLAC, OGG via FFmpeg conversion[1]
- **Quality Preservation**: Maintain audio quality during format conversion
- **Priority**: Low
- **Dependencies**: 4.1

#### 8.2 Output Enhancement Options
- **Task**: Implement additional output processing features
- **Features**:
  - Auto-trim silence from generated audio
  - Multiple output format support (16-bit PCM, different sample rates)
  - Metadata embedding in output files
- **Implementation**: Post-processing pipeline in handler
- **Priority**: Low
- **Dependencies**: 4.3

#### 8.3 Performance Monitoring
- **Task**: Add performance metrics and monitoring
- **Metrics**: Processing time, memory usage, success/failure rates
- **Implementation**: Logging system with structured output
- **Priority**: Low
- **Dependencies**: 7.2

## Technical Specifications

### Environment Requirements
- **Base Image**: `runpod/worker-comfyui:<version>-base`[3]
- **Python Version**: 3.10+ (inherited from base image)
- **GPU Requirements**: CUDA-compatible, ≥10GB VRAM recommended[1]
- **System Dependencies**: FFmpeg, Git, Git LFS[1]

### API Interface
- **Input Format**: JSON with `text`, `reference_audio`, optional parameters
- **Output Format**: JSON with `wav_paths` array and `prompt_id`
- **Processing**: Asynchronous via RunPod serverless API
- **Timeout**: 10-minute maximum processing time[1]

### Security Considerations
- **Authentication**: RunPod API key validation
- **Input Sanitization**: URL validation, file path security
- **Model Access**: Hugging Face token for private model access[1]
- **Network Security**: Restricted container network access

## Success Criteria

1. **Functional Requirements**:
   - Successfully process text + reference audio → WAV output
   - Support both URL and file path reference audio inputs
   - Handle multiple audio formats and sample rates
   - Maintain audio quality throughout processing pipeline

2. **Performance Requirements**:
   - Cold start time < 2 minutes for model loading
   - Processing time < 5 minutes for typical inputs
   - Memory usage within GPU VRAM limits
   - High success rate for valid inputs

3. **Deployment Requirements**:
   - Successful deployment on RunPod serverless platform
   - Stable operation under production load
   - Clear documentation for end-user deployment
   - Comprehensive error handling and logging

## Risk Mitigation

### High-Risk Items
1. **Model Compatibility**: Ensure ComfyUI-VibeVoice nodes work with target model versions
2. **Memory Management**: Prevent CUDA OOM errors during processing
3. **Audio Quality**: Maintain reference audio fidelity through processing pipeline

### Mitigation Strategies
1. **Version Pinning**: Lock specific versions of all dependencies
2. **Comprehensive Testing**: Test with various audio inputs and edge cases
3. **Graceful Degradation**: Implement fallback mechanisms for common failures
4. **Documentation**: Provide troubleshooting guides for common issues

This todo list provides a comprehensive roadmap for developing a production-ready RunPod worker that integrates ComfyUI with VibeVoice TTS capabilities, ensuring robust operation and easy deployment fornt for end users.

[1](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/23813136/06f2844e-45b0-45e6-bb38-e5e2e5f5d984/message-21.txt)
[2](https://github.com/runpod-workers/worker-comfyui)
[3](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/23813136/4d6af60a-f852-4516-af29-0be886d0b4bc/customization.md)
[4](https://github.com/wildminder/ComfyUI-VibeVoice)
[5](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/23813136/26615a2b-9e7f-419d-8ea2-268b34261cfc/custom-worker.md)
[6](https://github.com/BennyKok/comfy-deploy-runpod-worker)
[7](https://www.nextdiffusion.ai/tutorials/multi-speaker-audio-generation-microsoft-vibevoice-comfyui)
[8](https://github.com/diodiogod/TTS-Audio-Suite)
[9](https://docs.runpod.io/serverless/workers/github-integration)
[10](https://comfy.icu/extension/wildminder__ComfyUI-VibeVoice)
[11](https://microsoft.github.io/VibeVoice/)
[12](https://docs.runpod.io/tutorials/serverless/comfyui)
[13](https://huggingface.co/microsoft/VibeVoice-1.5B)
[14](https://www.reddit.com/r/StableDiffusion/comments/1n178o9/wip_comfyui_wrapper_for_microsofts_new_vibevoice/)
[15](https://www.reddit.com/r/StableDiffusion/comments/1nix2r4/the_new_indextts2_model_is_now_supported_on_tts/)
[16](https://github.com/blib-la/runpod-worker-comfy/releases)
[17](https://github.com/Enemyx-net/VibeVoice-ComfyUI)
[18](https://skywork.ai/blog/the-sound-of-the-future-a-deep-dive-into-microsofts-vibevoice/)
[19](https://hub.docker.com/r/timpietruskyblibla/runpod-worker-comfy)
[20](https://comfy.icu/extension/Enemyx-net__VibeVoice-ComfyUI)
[21](https://www.answeroverflow.com/m/1395165845084442724)
[22](https://www.youtube.com/watch?v=QsRQmx5OtOg)
[23](https://www.mikedegeofroy.com/blog/comfyui-serverless)
