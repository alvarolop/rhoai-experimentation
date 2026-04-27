#!/bin/bash
set -e

# Configuration
IMAGE_NAME="${IMAGE_NAME:-quay.io/alopezme/rhoai-kfp-builder}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
PUSH="${PUSH:-false}"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Building container image..."
echo "  Image: ${IMAGE_NAME}:${IMAGE_TAG}"
echo "  Push: ${PUSH}"

# Build with podman or docker
if command -v podman &> /dev/null; then
    BUILD_CMD="podman"
elif command -v docker &> /dev/null; then
    BUILD_CMD="docker"
else
    echo "Error: Neither podman nor docker found"
    exit 1
fi

echo "Using ${BUILD_CMD} to build image..."

${BUILD_CMD} build \
    -f "${SCRIPT_DIR}/Containerfile" \
    -t "${IMAGE_NAME}:${IMAGE_TAG}" \
    "${SCRIPT_DIR}"

echo "Image built successfully: ${IMAGE_NAME}:${IMAGE_TAG}"

if [ "${PUSH}" = "true" ]; then
    echo "Pushing image to registry..."
    ${BUILD_CMD} push "${IMAGE_NAME}:${IMAGE_TAG}"
    echo "Image pushed successfully"
else
    echo "Skipping push (set PUSH=true to push)"
fi

echo ""
echo "To use this image, update chart/values.yaml:"
echo "  tekton.image: ${IMAGE_NAME}:${IMAGE_TAG}"
