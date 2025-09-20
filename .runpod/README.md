# VibeVoice TTS RunPod Deployment

This directory contains the configuration files and documentation for deploying the VibeVoice TTS worker on RunPod serverless platform.

## Quick Start

### Prerequisites
- RunPod account with serverless access
- Docker registry access (Docker Hub, ECR, etc.)
- Hugging Face token (for model downloads)

### Deployment Steps

1. **Configure Environment**
   ```bash
   # Set your environment variables
   export HF_TOKEN="your_huggingface_token"
   export DOCKER_REGISTRY="your-registry.com"
   ```

2. **Run Deployment Script**
   ```bash
   cd scripts
   python deploy_runpod.py --registry $DOCKER_REGISTRY
   ```

3. **Verify Deployment**
   - Check RunPod dashboard for endpoint status
   - Run tests using the provided test configurations

## Configuration Files

### hub.json
Main deployment configuration for RunPod serverless:
- **GPU**: RTX 4090 (24GB VRAM) or RTX 3090 (24GB VRAM)
- **Memory**: 50GB container disk
- **Scaling**: Auto-scaling with min 1, max 5 instances
- **Environment**: Configurable model cache and network volume settings

### tests.json
Test configurations for TTS functionality:
- Basic TTS generation test
- Reference audio voice cloning test
- Performance validation tests

### deployment.json (Generated)
Complete deployment configuration with:
- Docker image reference
- Scaling policies
- Network volume mounts
- Environment variables

## Optimization Features

### Auto-Scaling Configuration
- **Min Instances**: 1 (cost optimization)
- **Max Instances**: 5 (high-throughput)
- **Target Concurrency**: 2 requests per instance
- **Scale-up Threshold**: 80% utilization
- **Scale-down Threshold**: 30% utilization

### Caching Strategies
- **Model Cache**: 25GB LRU cache for TTS models
- **Dependency Cache**: Pip, conda, and HuggingFace caches
- **Workflow Cache**: Intermediate result caching
- **Network Cache**: HTTP and DNS caching

### VRAM Optimization
- **Memory Efficient Loading**: Automatic device mapping
- **Mixed Precision**: FP16 inference
- **Flash Attention**: Optimized attention mechanisms
- **Dynamic Batching**: Adaptive batch processing

### Network Volumes
- **Model Storage**: 100GB persistent volume for models
- **Cache Storage**: 50GB fast storage for caches
- **Output Storage**: 25GB for generated audio files
- **Config Storage**: 5GB for configuration files

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REFRESH_WORKER` | Clean state after each job | `false` |
| `MODEL_CACHE_SIZE` | Model cache size in GB | `20` |
| `ENABLE_NETWORK_VOLUME` | Use persistent storage | `true` |
| `AUTO_SCALE_MIN` | Minimum instances | `1` |
| `AUTO_SCALE_MAX` | Maximum instances | `5` |

## Monitoring & Metrics

### Performance Metrics
- Inference time per request
- GPU utilization percentage
- Memory usage (VRAM/RAM)
- Cache hit/miss rates

### Health Checks
- Model loading status
- GPU memory availability
- Network connectivity
- Disk space monitoring

## Testing

### Local Testing
```bash
# Run basic TTS test
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "text": "Hello, world!",
      "temperature": 0.8,
      "speed": 1.0,
      "seed": 42
    }
  }'
```

### RunPod Testing
Use the provided `tests.json` configuration in RunPod dashboard or CLI.

## Troubleshooting

### Common Issues

**High Latency**
- Check GPU utilization
- Verify model cache is working
- Monitor network volume performance

**Out of Memory**
- Reduce batch size in configuration
- Enable gradient checkpointing
- Check for memory leaks in workflow

**Model Loading Failures**
- Verify HuggingFace token
- Check network volume permissions
- Ensure sufficient disk space

### Logs & Debugging
- Enable debug logging in environment variables
- Check RunPod dashboard for instance logs
- Monitor GPU metrics in real-time

## Performance Tuning

### For Cost Optimization
- Set lower auto-scaling thresholds
- Use smaller batch sizes
- Enable more aggressive caching

### For High Throughput
- Increase max instances
- Use larger batch sizes
- Optimize model loading strategies

### For Low Latency
- Pre-load models on startup
- Use faster storage options
- Optimize network configuration

## Security Considerations

- Store HuggingFace tokens securely
- Use encrypted network volumes
- Implement proper access controls
- Regular security updates for base images

## Additional Resources

- [RunPod Documentation](https://docs.runpod.io/)
- [ComfyUI Documentation](https://docs.comfy.org/)
- [VibeVoice Model Documentation](https://github.com/aoi-ot/VibeVoice)

## Support

For issues specific to this deployment:
1. Check the troubleshooting section above
2. Review RunPod serverless logs
3. Verify configuration files are correct
4. Test with minimal configuration first

For VibeVoice or ComfyUI issues, refer to their respective documentation and communities.
