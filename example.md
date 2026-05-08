<div align="center">

# DiaMate: Diabetic Foot Ulcer Segmentation

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?logo=python&style=flat-square" alt="Python 3.11" />
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&style=flat-square" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PyTorch-2.11+-EE4C2C?logo=pytorch&style=flat-square" alt="PyTorch" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License" />
</div>

**AI-powered semantic segmentation for diabetic foot ulcer**

A production-ready REST API that detects and segments diabetic foot ulcers in smartphone images using a deep U-Net model, returning detailed wound analysis including coverage metrics and visual overlays.

</div>

---

## Table of Contents
- [Features](#features)
- [Quick Start](#quick-start)
- [Philosophy](#philosophy)
- [Installation](#installation)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)
- [Model Architecture](#model-architecture)
- [Configuration](#configuration)
- [Development](#development)
- [Contributing](#contributing)
- [Citation](#citation)
- [License](#license)

## Features
- **Deep Learning Model**: U-Net architecture trained from scratch for DFU segmentation
- **Fast Inference**: GPU-accelerated predictions with inference timing
- **Binary Mask Output**: Precise pixel-level ulcer region identification
- **Visual Overlays**: Base64-encoded highlight overlays for easy visualization
- **Wound Metrics**: Automatic computation of ulcer coverage percentage and statistics
- **Production API**: FastAPI-based REST service with comprehensive error handling
- **Device Flexible**: Runs on CPU or GPU with automatic device detection

## Quick Start

### Run the API Server
```bash
# Install dependencies
uv sync

# Start the FastAPI server
python -m uvicorn src.main:app --reload --port 5000
```

### Segment an Image
```python
import requests
import base64

# Prepare image
with open('foot_image.jpg', 'rb') as f:
    image_b64 = base64.b64encode(f.read()).decode()

# Send to API
response = requests.post(
    'http://localhost:8000/api/v1/segmentation/',
    json={'image_b64': image_b64}
)

result = response.json()
print(f"Ulcer Detected: {result['ulcer_detected']}")
print(f"Coverage: {result['ulcer_coverage']:.2f}%")
print(f"Inference Time: {result['inference_ms']:.1f}ms")
```

### Interactive API Documentation
Once running, visit:
- **Swagger UI**: http://localhost:5000/docs
- **ReDoc**: http://localhost:5000/redoc

## Philosophy

DiaMate was developed as part of a graduation project at Benha Faculty of Computers and Artificial Intelligence (BFCAI), Benha University. We believe that:

**AI can democratize healthcare** — Diabetic foot ulcers are a serious complication affecting millions globally, particularly in resource-limited settings. Our goal is to provide clinicians and patients with fast, reliable, AI-assisted wound assessment tools that work with smartphone images.

**Simple tools work best** — Rather than building a complex system, we focused on a single, well-defined task: accurate ulcer segmentation. This modular approach makes the system easy to integrate, maintain, and improve.

**Transparency matters** — We provide detailed metrics (ulcer coverage %, pixel counts) and visual outputs (masks, overlays) so users understand what the model detected and can make informed clinical decisions.

## Installation

### Requirements
- Python 3.11+
- CUDA 12.8 (for GPU acceleration, optional but recommended)
- 2GB+ RAM for CPU, 2GB+ VRAM for GPU

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/MohamedHamed05/Diabetic-Foot-Ulcer-Segmentation.git
   cd Diabetic-Foot-Ulcer-Segmentation
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   
   # Activate (Windows)
   .venv\Scripts\activate
   
   # Activate (macOS/Linux)
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   # Using pip
   pip install -r requirements.txt
   
   # Or using uv (faster alternative)
   uv sync
   ```

4. **Start the server**
   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8000
   ```

## API Endpoints

### `POST /api/v1/segmentation/`

Segment an image and detect diabetic foot ulcers.

**Request Body:**
```json
{
  "image_b64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
}
```

**Response (Success - 200):**
```json
{
  "ulcer_detected": true,
  "ulcer_pixels": 1250,
  "total_pixels": 262144,
  "ulcer_coverage": 4.77,
  "inference_ms": 145.3,
  "mask_b64": "iVBORw0KGgoAAAANSUhEUg...",
  "overlay_b64": "iVBORw0KGgoAAAANSUhEUg..."
}
```

**Error Responses:**
| Status | Signal | Description |
|--------|--------|-------------|
| 400 | IMAGE_EMPTY | Provided image is empty |
| 413 | IMAGE_TOO_LARGE | Image exceeds maximum size limit |
| 422 | INVALID_IMAGE | Image cannot be decoded or is invalid |
| 422 | IMAGE_TOO_SMALL | Image dimensions are below minimum (256×256) |

### `GET /health`

Health check endpoint to verify API is running.

**Response:**
```json
{
  "model_loaded": True,
  "device": "cuda", # or "cpu"
  "signal": "Model is loaded"
}
```

## Project Structure

```
Diabetic-Foot-Ulcer-Segmentation/
├── src/
│   ├── main.py                      # FastAPI application entry point
│   ├── controllers/
│   │   └── seg_controller.py        # Model inference logic
│   ├── routers/
│   │   ├── base.py                  # Health check routes
│   │   └── seg_route.py             # Segmentation endpoint
│   ├── model/
│   │   ├── unet.py                  # U-Net model architecture
│   │   ├── unet.pth                 # Trained model weights
│   │   ├── schemes.py               # Request/response schemas
│   │   └── enums/
│   │       └── enums.py             # Error codes and signals
│   └── util/
│       ├── config.py                # Configuration management
│       └── utility.py               # Helper functions
├── pyproject.toml                   # Project metadata (uv)
├── requirements.txt                 # Python dependencies
├── LICENSE                          # MIT License
└── README.md                         # This file
```

## Model Architecture

### U-Net Overview

DiaMate uses a **U-Net** convolutional neural network trained from scratch for precise diabetic foot ulcer segmentation. The U-Net architecture is specifically designed for medical image segmentation tasks, combining:

- **Encoder Path**: Successive convolutional layers with max pooling to extract features at multiple scales
- **Bottleneck**: Deep feature extraction at the lowest resolution
- **Decoder Path**: Transpose convolutions to progressively upsample features back to input resolution
- **Skip Connections**: Direct connections from encoder to decoder layers to preserve fine-grained spatial information

### Architecture Specifications

**Channel Configuration:**
- **Encoder levels**: 64 → 128 → 256 → 512 → 1024 channels (5 levels of progressive downsampling)
- **Decoder levels**: 1024 → 512 → 256 → 128 → 64 channels (5 levels of progressive upsampling)
- **Final output**: 1 channel (binary segmentation mask)

**Input/Output:**
- **Input**: 512×512 RGB images, normalized to ImageNet statistics (mean: [0.485, 0.456, 0.406], std: [0.229, 0.224, 0.225])
- **Output**: 512×512 binary mask (ulcer probability map, values 0-1 after sigmoid activation)

**Activation & Regularization:**
- **Activation**: ReLU (Rectified Linear Unit) with batch normalization after each convolution
- **Regularization**: Dropout (0.1) in bottleneck to prevent overfitting
- **Final activation**: Sigmoid for binary classification

### Model Size & Performance

**Model Capacity:**
| Metric | Value |
|--------|-------|
| **Total Parameters** | 31,037,633 |
| **Trainable Parameters** | 31,037,633 |
| **Parameter Size** | ~124.15 MB |
| **Estimated Total Size** | ~2.43 GB (including forward/backward pass) |
| **Input Size** | 3.15 MB |

### Test Set Results

**Performance Metrics:**
| Metric | Value |
|--------|-------|
| **Loss (BCE + Dice)** | 0.3817 |
| **Dice Coefficient** | 0.8192 |
| **Intersection over Union (IoU)** | 0.7392 |
| **Pixel Accuracy** | 0.6787 |
| **Precision** | 0.8199 |
| **Recall** | 0.8933 |

The model achieved strong performance on the test set with a Dice coefficient of 0.82, indicating excellent overlap between predicted and ground truth segmentations. High recall (0.89) ensures minimal false negatives—critical for clinical applications where missing ulcer regions could be dangerous.

### Training History

The model was trained for 70 epochs using combined BCE and Dice loss. The following graphs illustrate training progression:

**Loss Convergence:**
![BCF+Dice Loss](src/assets/images/Dice_coeff.png)

**Dice Coefficient Evolution:**
![Dice Coefficient](src/assets/images/Dice_coeff.png)

**IoU (Jaccard Index) Progress:**
![IoU Jaccard](src/assets/images/iou.png)

All metrics show consistent convergence with validation performance stabilizing around epoch 54, indicating robust learning without significant overfitting.

### Configuration

Default model configuration in [src/util/config.py](src/util/config.py):

```python
img_size = 512                 # Input/output image size (pixels)
input_channels = 3            # RGB input
output_channels = 1           # Binary segmentation
feature_channels = [64, 128, 256, 512, 1024]  # U-Net channel configuration
threshold = 0.5               # Probability threshold for binary mask
device = 'cuda' if torch.cuda.is_available() else 'cpu'  # Auto device selection
```

Implementation details available in [src/model/unet.py](src/model/unet.py).

## Development

### Running Locally
```bash
# Development server with auto-reload
uvicorn src.main:app --reload

# With specific host and port
uvicorn src.main:app --host 0.0.0.0 --port 5000
```

### Testing the API
Use the included Postman collection at [src/assets/DiaMate-DFU.postman_collection.json](src/assets/DiaMate-DFU.postman_collection.json):

1. Import into Postman
2. Run the Segmentation request with a test image

### Debugging
- **Verbose Logging**: Check console output for model loading and inference metrics
- **API Docs**: Visit `http://localhost:5000/docs` for interactive testing
- **Error Signals**: Check response signals in [src/model/enums/enums.py](src/model/enums/enums.py)

## License

MIT License — see [LICENSE](LICENSE) file for details.

This project is provided as-is for research and educational purposes. **Not approved for clinical use without proper validation and regulatory compliance.**

---

<div align="center">
  <p>
    Built with ❤️ at
    <a href="https://fci.bu.edu.eg/">Benha Faculty of Computers and Artificial Intelligence</a>
  </p>
  <p>
    <strong>Disclaimer</strong>: This tool is intended for research and educational purposes only. 
    Always consult qualified healthcare professionals for medical advice.
  </p>
</div>
