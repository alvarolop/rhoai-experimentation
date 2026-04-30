#!/bin/bash
set -e

# Configuration
IMAGE_NAME="${IMAGE_NAME:-quay.io/alopezme/rhoai-experimentation-kfp}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

echo "====================================="
echo "Verifying KFP Component Image"
echo "====================================="
echo ""
echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""

# Check if podman is available
if ! command -v podman &> /dev/null; then
    echo "Error: podman not found. Please install podman."
    exit 1
fi

echo "1. Pulling image..."
podman pull "${IMAGE_NAME}:${IMAGE_TAG}"
echo "   ✅ Image pulled successfully"
echo ""

echo "2. Checking image size..."
SIZE=$(podman image inspect "${IMAGE_NAME}:${IMAGE_TAG}" --format '{{.Size}}' | awk '{print $1/1024/1024 " MB"}')
echo "   Image size: ${SIZE}"
echo ""

echo "3. Verifying Python version..."
PYTHON_VERSION=$(podman run --rm "${IMAGE_NAME}:${IMAGE_TAG}" python3 --version)
echo "   ${PYTHON_VERSION}"
echo ""

echo "4. Verifying ML libraries..."
SKLEARN_VERSION=$(podman run --rm "${IMAGE_NAME}:${IMAGE_TAG}" python3 -c "import sklearn; print(f'scikit-learn {sklearn.__version__}')")
PANDAS_VERSION=$(podman run --rm "${IMAGE_NAME}:${IMAGE_TAG}" python3 -c "import pandas; print(f'pandas {pandas.__version__}')")
NUMPY_VERSION=$(podman run --rm "${IMAGE_NAME}:${IMAGE_TAG}" python3 -c "import numpy; print(f'numpy {numpy.__version__}')")
echo "   ✅ ${SKLEARN_VERSION}"
echo "   ✅ ${PANDAS_VERSION}"
echo "   ✅ ${NUMPY_VERSION}"
echo ""

echo "5. Verifying ONNX support..."
ONNX_VERSION=$(podman run --rm "${IMAGE_NAME}:${IMAGE_TAG}" python3 -c "import onnx; print(f'onnx {onnx.__version__}')")
SKL2ONNX_CHECK=$(podman run --rm "${IMAGE_NAME}:${IMAGE_TAG}" python3 -c "import skl2onnx; print('skl2onnx installed')")
echo "   ✅ ${ONNX_VERSION}"
echo "   ✅ ${SKL2ONNX_CHECK}"
echo ""

echo "6. Verifying infrastructure clients..."
BOTO3_CHECK=$(podman run --rm "${IMAGE_NAME}:${IMAGE_TAG}" python3 -c "import boto3; print('boto3 installed')")
K8S_CHECK=$(podman run --rm "${IMAGE_NAME}:${IMAGE_TAG}" python3 -c "import kubernetes; print('kubernetes client installed')")
REQUESTS_CHECK=$(podman run --rm "${IMAGE_NAME}:${IMAGE_TAG}" python3 -c "import requests; print('requests installed')")
echo "   ✅ ${BOTO3_CHECK}"
echo "   ✅ ${K8S_CHECK}"
echo "   ✅ ${REQUESTS_CHECK}"
echo ""

echo "====================================="
echo "✅ All verifications passed!"
echo "====================================="
echo ""
echo "This image can be used in KFP components:"
echo "  base_image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "  packages_to_install: []  # No packages needed!"
echo ""
echo "Full package list:"
podman run --rm "${IMAGE_NAME}:${IMAGE_TAG}" pip list
