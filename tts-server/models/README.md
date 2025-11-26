# Voice Models Directory

This directory contains ONNX voice models for the Piper TTS engine.

## Required Files

Place your voice model files here:
- `*.onnx` - The voice model (e.g., `skeletor_v1.onnx`)
- `*.onnx.json` - Model configuration (e.g., `skeletor_v1.onnx.json`)

## Default Model

The server expects:
- `skeletor_v1.onnx`
- `skeletor_v1.onnx.json`

You can override this with command-line arguments:
```bash
python ../timmy_speaks_cuda.py --model your_model.onnx --config your_model.onnx.json
```

## Where to Get Models

### Option 1: Use Existing Models
If you have models from `C:\Users\dsm27\piper\models\`:
```bash
copy C:\Users\dsm27\piper\models\*.onnx .
copy C:\Users\dsm27\piper\models\*.json .
```

### Option 2: Download from Piper
Visit the official Piper TTS repository for pre-trained voices:
- https://github.com/rhasspy/piper
- Look for voice models in ONNX format

### Option 3: Train Your Own
Follow Piper's training guide to create custom voices:
- https://github.com/rhasspy/piper/blob/master/TRAINING.md

## Model Storage

**Why aren't models in Git?**
- Voice models are large (100-500 MB each)
- Git is not optimized for binary files
- Models are kept separately to reduce repository size

## File Size Notes

Typical model sizes:
- `tiny` models: ~40 MB
- `small` models: ~100-200 MB
- `medium` models: ~350-500 MB
- `large` models: ~1 GB+

The `skeletor_v1` model is approximately 350 MB.

