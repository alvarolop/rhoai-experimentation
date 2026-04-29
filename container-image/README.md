# Custom Builder Image

This directory contains the container image definition with pre-installed tools for Kubeflow Pipelines CI/CD.

## Why a Custom Image?

Instead of installing dependencies in every Tekton pipeline run, we build a custom image with:
- ✅ Faster pipeline execution (no install step)
- ✅ Consistent environment across runs
- ✅ Reduced network traffic
- ✅ Offline capability

## Image Contents

**Base:** `registry.access.redhat.com/ubi9/python-311` (Red Hat Universal Base Image 9 with Python 3.11)

**System Tools:**
- git
- curl
- ca-certificates

**Python Packages:**
- `kfp==2.8.0` - Kubeflow Pipelines SDK
- `scikit-learn==1.5.0` - ML library (for pipeline components)
- `pandas==2.2.2` - Data manipulation
- `numpy==1.26.4` - Numerical computing
- `requests==2.32.3` - HTTP client
- `pylint==3.1.0` - Python linter
- `flake8==7.0.0` - Code style checker
- `black==24.3.0` - Code formatter

## Building the Image

### Prerequisites

- Podman or Docker installed
- Access to container registry (Quay.io, Docker Hub, internal registry)

### Build Locally

From the `container-image/` directory:

```bash
cd container-image
./build-image.sh
```

Or with custom settings:

```bash
cd container-image
IMAGE_NAME=quay.io/myorg/kfp-builder \
IMAGE_TAG=v1.0 \
PUSH=false \
./build-image.sh
```

### Build and Push

```bash
cd container-image

# Login to registry
podman login quay.io

# Build and push
IMAGE_NAME=quay.io/alopezme/rhoai-kfp-builder \
IMAGE_TAG=v1.0 \
PUSH=true \
./build-image.sh
```

### Build with Podman/Docker Directly

```bash
cd container-image

# Build
podman build -f Containerfile -t quay.io/alopezme/rhoai-kfp-builder:latest .

# Push
podman push quay.io/alopezme/rhoai-kfp-builder:latest
```

## Using the Custom Image

Update `chart/values.yaml`:

```yaml
tekton:
  image: quay.io/alopezme/rhoai-kfp-builder:v1.0
```

Or override during Helm install:

```bash
helm install fraud-detection chart/ \
  --set tekton.image=quay.io/alopezme/rhoai-kfp-builder:v1.0
```

## Automated Builds

### GitHub Actions

Create `.github/workflows/build-image.yaml`:

```yaml
name: Build Container Image

on:
  push:
    branches: [main]
    paths:
      - 'container-image/**'
      - 'pipelines/**/requirements.txt'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to Quay.io
        uses: docker/login-action@v3
        with:
          registry: quay.io
          username: ${{ secrets.QUAY_USERNAME }}
          password: ${{ secrets.QUAY_PASSWORD }}
      
      - name: Build and push
        run: |
          cd container-image
          IMAGE_NAME=quay.io/alopezme/rhoai-kfp-builder
          IMAGE_TAG=${{ github.sha }}
          PUSH=true
          ./build-image.sh
```

### OpenShift BuildConfig

```yaml
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  name: kfp-builder
spec:
  source:
    git:
      uri: https://github.com/alvarolop/rhoai-experimentation.git
      ref: main
    contextDir: container-image
  strategy:
    dockerStrategy:
      dockerfilePath: Containerfile
  output:
    to:
      kind: ImageStreamTag
      name: rhoai-kfp-builder:latest
```

Trigger build:
```bash
oc start-build kfp-builder -n <namespace>
```

## Updating Dependencies

When you need to update Python packages:

1. Edit `Containerfile` - change package versions
2. Rebuild the image:
   ```bash
   PUSH=true ./build-image.sh
   ```
3. Update Helm values or redeploy

## Image Variants

### Minimal (Smaller Size)

Remove unused packages from `Containerfile`:

```dockerfile
RUN pip install --no-cache-dir \
    kfp==2.8.0 \
    requests==2.32.3 \
    pylint==3.1.0
```

### GPU-Enabled

Change base image:

```dockerfile
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04
```

### With Model Registry Client

Add model registry SDK:

```dockerfile
RUN pip install --no-cache-dir \
    model-registry==0.2.0
```

## Security

- **Red Hat UBI9-based**: Official Red Hat Universal Base Image with enterprise support
- Image runs as non-root user (UID 1001)
- OpenShift-compatible (supports arbitrary user IDs)
- No secrets baked into image
- Regular security scanning recommended

Scan with:
```bash
podman scan quay.io/alopezme/rhoai-kfp-builder:latest
```

Or use Quay.io's built-in security scanner.

## Image Size

Approximate size: **~400MB**

Breakdown:
- Base python:3.11-slim: ~150MB
- System packages: ~50MB
- Python packages: ~200MB

Compare to installing each run:
- Network transfer: ~200MB per run
- Install time: ~2-3 minutes per run

## Troubleshooting

### Image Pull Failures

Check registry access:
```bash
oc get secret -n <namespace>
```

Create pull secret if needed:
```bash
oc create secret docker-registry quay-secret \
  --docker-server=quay.io \
  --docker-username=<username> \
  --docker-password=<password> \
  -n <namespace>
```

Link to ServiceAccount:
```bash
oc secrets link pipeline quay-secret --for=pull -n <namespace>
```

### Version Conflicts

If pipeline components fail with import errors, check package versions in `Containerfile` match `pipelines/fraud-detection/requirements.txt`.

### Build Failures

Common issues:
- Network timeout → retry build
- Out of disk space → clean images: `podman image prune -a`
- Permission denied → check registry credentials
