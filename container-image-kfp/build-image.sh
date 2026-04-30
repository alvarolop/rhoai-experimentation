#!/bin/bash
set -e

# Configuration
IMAGE_NAME="${IMAGE_NAME:-quay.io/alopezme/rhoai-experimentation-kfp}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
PUSH="${PUSH:-false}"

echo "====================================="
echo "Building KFP Component Image"
echo "====================================="
echo ""
echo "  Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "  Push: ${PUSH}"
echo ""

# Check if podman is available
if ! command -v podman &> /dev/null; then
    echo "Error: podman not found. Please install podman."
    exit 1
fi

echo "Building container image..."
podman build -f Containerfile -t "${IMAGE_NAME}:${IMAGE_TAG}" .

echo ""
echo "✅ Image built successfully"
echo ""

if [ "${PUSH}" = "true" ]; then
    echo "Pushing to registry..."
    podman push "${IMAGE_NAME}:${IMAGE_TAG}"
    echo ""
    echo "✅ Image pushed to ${IMAGE_NAME}:${IMAGE_TAG}"
    echo ""
else
    echo "ℹ️  Skipping push (set PUSH=true to push)"
    echo ""
fi

echo "====================================="
echo "Next steps:"
echo "====================================="
echo ""
echo "1. Verify image:"
echo "   ./verify-image.sh"
echo ""
echo "2. Test locally:"
echo "   podman run -it --rm ${IMAGE_NAME}:${IMAGE_TAG} bash"
echo ""
echo "3. Update pipeline components to use this image"
echo ""
