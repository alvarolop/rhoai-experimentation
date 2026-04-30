# Kubeflow Pipeline Component Image

Custom container image for **Kubeflow Pipeline components** in disconnected/air-gapped OpenShift environments.

## Purpose

This image is for **Kubeflow pipeline components** that execute as pods in the Data Science Pipelines runtime:
- ✅ **Data generation** (`generate_fraud_data`) - Synthetic dataset creation
- ✅ **Model training** (`train_fraud_model`) - ML model training with scikit-learn
- ✅ **Model export** (`export_to_s3`) - ONNX conversion and S3 upload
- ✅ **Model registration** (`register_model_real`) - Model Registry integration
- ✅ **Deployment** (`deploy_openvino`) - KServe InferenceService creation
- ✅ **Monitoring** (`configure_trustyai`) - TrustyAI setup for bias detection
- ✅ **Validation** (`validate_pipeline`) - Pre-flight checks

**Important:** This is different from the Tekton image. The Tekton image is for CI/CD tasks; this image is for runtime pipeline components.

## Why a Custom Image?

### Disconnected Environment Requirements

In disconnected/air-gapped environments:
- ❌ **Cannot run `pip install` during component execution** (no PyPI access)
- ❌ **Cannot use base Python images** (missing required packages)
- ✅ **Must pre-install all dependencies** at image build time

### Current Problem

Components use `packages_to_install` which installs packages at runtime:

```python
@component(
    base_image="registry.access.redhat.com/ubi9/python-312",
    packages_to_install=["pandas==2.3.0", "scikit-learn==1.7.0"],  # ❌ Fails in disconnected
)
def train_fraud_model(...):
    ...
```

**Runtime behavior:**
1. Pod starts with base UBI9 Python image
2. KFP SDK runs `pip install pandas scikit-learn` → ❌ **Fails (no internet)**
3. Component never executes

### Our Solution

Pre-built image with all dependencies:

```python
@component(
    base_image="quay.io/alopezme/rhoai-experimentation-kfp:latest",
    packages_to_install=[],  # ✅ No pip install needed
)
def train_fraud_model(...):
    ...
```

**Runtime behavior:**
1. Pod starts with our custom image (all packages pre-installed)
2. No pip install needed
3. Component executes immediately ✅

## Image Contents

### Base Image

`registry.access.redhat.com/ubi9/python-312` (Red Hat Universal Base Image 9)

### Python Packages

**ML and Data Science Libraries:**
- `scikit-learn==1.7.0` - Machine learning
- `pandas==2.3.0` - Data manipulation
- `numpy==2.3.0` - Numerical computing

**Model Export and Conversion:**
- `skl2onnx==1.18.0` - ONNX model conversion
- `onnx==1.17.0` - ONNX format support

**Infrastructure Clients:**
- `boto3==1.37.0` - AWS S3 client (MinIO compatible)
- `kubernetes==31.0.0` - Kubernetes API client
- `requests==2.32.3` - HTTP client

### Package Version Strategy

Uses the **superset** of all component requirements:
- `data_generator` needs pandas 2.2.2, numpy 1.26.4 → Covered by 2.3.0 and 2.3.0
- `train_model` needs pandas 2.3.0, sklearn 1.7.0, numpy 2.3.0 → Exact match
- `export_to_s3` needs sklearn, onnx, skl2onnx, boto3 → Included
- `deploy_openvino` needs kubernetes → Included
- `configure_trustyai` needs kubernetes → Included
- `validate_pipeline` needs requests → Included
- `register_model_real` needs requests → Included

### Security Features

- ✅ Red Hat UBI9-based (enterprise support)
- ✅ Non-root user (UID 1001)
- ✅ OpenShift-compatible (arbitrary user IDs)
- ✅ No secrets in image
- ✅ Minimal attack surface

## Building the Image

### Prerequisites

- Podman or Docker installed
- Access to Quay.io (or your container registry)
- Credentials for pushing images

### Quick Build

```bash
cd container-image-kfp

# Login to registry
podman login quay.io

# Build and push
IMAGE_NAME=quay.io/alopezme/rhoai-experimentation-kfp \
IMAGE_TAG=latest \
PUSH=true \
./build-image.sh
```

### Build Locally (No Push)

```bash
cd container-image-kfp
./build-image.sh
```

Output:
```
Building KFP Component Image...
  Image: quay.io/alopezme/rhoai-experimentation-kfp:latest
  Push: false
...
Image built successfully
```

### Build with Custom Tag

```bash
cd container-image-kfp
IMAGE_NAME=quay.io/alopezme/rhoai-experimentation-kfp \
IMAGE_TAG=v1.0.0 \
PUSH=true \
./build-image.sh
```

## Using the Image

### Update Component Definitions

Edit component files in `pipelines/fraud-detection/components/*.py`:

**Before (runtime pip install):**
```python
@component(
    base_image="registry.access.redhat.com/ubi9/python-312",
    packages_to_install=["pandas==2.3.0", "scikit-learn==1.7.0", "numpy==2.3.0"],
)
def train_fraud_model(...):
    ...
```

**After (pre-installed):**
```python
@component(
    base_image="quay.io/alopezme/rhoai-experimentation-kfp:latest",
    packages_to_install=[],
)
def train_fraud_model(...):
    ...
```

### Verify Image

```bash
cd container-image-kfp
./verify-image.sh
```

Output:
```
=====================================
Verifying KFP Component Image
=====================================

Image: quay.io/alopezme/rhoai-experimentation-kfp:latest

1. Pulling image...
   ✅ Image pulled successfully

2. Checking image size...
   Image size: ~600 MB

3. Verifying Python version...
   Python 3.12.x

4. Verifying ML libraries...
   ✅ scikit-learn 1.7.0
   ✅ pandas 2.3.0
   ✅ numpy 2.3.0

5. Verifying ONNX support...
   ✅ onnx 1.17.0
   ✅ skl2onnx installed

6. Verifying infrastructure clients...
   ✅ boto3 installed
   ✅ kubernetes client installed
   ✅ requests installed

=====================================
✅ All verifications passed!
=====================================
```

## Automated Builds (GitHub Actions)

**✅ Configured** in `.github/workflows/build-push-kfp-image.yaml`

The workflow automatically:
- Triggers on changes to `container-image-kfp/Containerfile`
- Builds multi-arch (amd64 + arm64)
- Pushes to Quay.io
- Tags with `latest`, commit SHA

### Setup GitHub Secrets

Same secrets as Tekton image (already configured):
1. `QUAY_REPO_USERNAME` - Your Quay.io username or robot account name
2. `QUAY_REPO_TOKEN` - Quay.io password or robot token

### Manual Trigger

```bash
# Via GitHub UI
Actions → Build and Push KFP Component Image → Run workflow

# Or push a commit
git commit -m "Update KFP image dependencies"
git push
```

## Disconnected Environment Workflow

### 1. Build in Connected Environment

```bash
podman build -f Containerfile -t quay.io/alopezme/rhoai-experimentation-kfp:v1.0.0 .
podman push quay.io/alopezme/rhoai-experimentation-kfp:v1.0.0
```

### 2. Mirror to Disconnected Registry

```bash
# From connected environment, mirror to disconnected registry
skopeo copy \
  docker://quay.io/alopezme/rhoai-experimentation-kfp:v1.0.0 \
  docker://registry.disconnected.local/rhoai/kfp-components:v1.0.0
```

### 3. Update Components

```python
@component(
    base_image="registry.disconnected.local/rhoai/kfp-components:v1.0.0",
    packages_to_install=[],
)
def train_fraud_model(...):
    ...
```

## Updating Dependencies

When updating Python packages or versions:

### 1. Update Containerfile

Edit `container-image-kfp/Containerfile`:

```dockerfile
RUN pip install --no-cache-dir \
    scikit-learn==1.8.0 \  # Updated version
    ...
```

### 2. Rebuild and Push

```bash
cd container-image-kfp
IMAGE_TAG=v1.1.0 PUSH=true ./build-image.sh
```

### 3. Update Component Definitions

```python
@component(
    base_image="quay.io/alopezme/rhoai-experimentation-kfp:v1.1.0",
    packages_to_install=[],
)
```

## Performance Benefits

### Without Custom Image (Base Python + pip install)

```
Component execution time:
├── Pull base image: ~10s
├── pip install pandas: ~30s
├── pip install sklearn: ~40s
├── pip install onnx: ~20s
├── Actual component work: ~30s
└── Total: ~130s
```

### With Custom Image (Pre-installed)

```
Component execution time:
├── Pull custom image: ~20s (first time only, then cached)
├── Actual component work: ~30s
└── Total: ~50s
```

**Savings:** ~80 seconds per component run (~62% faster)

**Pipeline with 7 components:** ~560 seconds saved (~9 minutes faster)

## Image Size

Approximate size: **~600MB**

Breakdown:
- UBI9 Python 3.12 base: ~200MB
- Python packages: ~400MB

## Troubleshooting

### Image Pull Failures

**Error:**
```
Failed to pull image: unauthorized
```

**Solution - Create Pull Secret:**

```bash
# Create pull secret
oc create secret docker-registry quay-pull-secret \
  --docker-server=quay.io \
  --docker-username=<username> \
  --docker-password=<password> \
  -n <namespace>

# Link to pipeline ServiceAccount
oc secrets link pipeline quay-pull-secret --for=pull -n <namespace>
```

### Import Errors in Components

**Error:**
```
ModuleNotFoundError: No module named 'sklearn'
```

**Solutions:**

1. Verify component uses the custom image:
   ```python
   base_image="quay.io/alopezme/rhoai-experimentation-kfp:latest"
   ```

2. Check packages_to_install is empty or removed:
   ```python
   packages_to_install=[]  # Or omit this parameter
   ```

3. Verify image exists and is pullable:
   ```bash
   podman pull quay.io/alopezme/rhoai-experimentation-kfp:latest
   ```

4. Verify packages are installed in image:
   ```bash
   podman run --rm quay.io/alopezme/rhoai-experimentation-kfp:latest pip list | grep sklearn
   ```

### Version Conflicts

If you encounter version conflicts:

1. Check the Containerfile uses compatible versions
2. Test locally before pushing:
   ```bash
   podman run -it --rm quay.io/alopezme/rhoai-experimentation-kfp:latest bash
   python3 -c "import sklearn, pandas, numpy; print('All imports successful')"
   ```

## Testing the Image

### Test Locally

```bash
# Run container
podman run -it --rm quay.io/alopezme/rhoai-experimentation-kfp:latest bash

# Inside container, verify packages
python3 -c "import sklearn; print(f'scikit-learn: {sklearn.__version__}')"
python3 -c "import pandas; print(f'pandas: {pandas.__version__}')"
python3 -c "import numpy; print(f'numpy: {numpy.__version__}')"
python3 -c "import boto3; print('boto3 installed')"
python3 -c "import kubernetes; print('kubernetes client installed')"
```

### Test in Pipeline

After updating component definitions, compile and run the pipeline:

```bash
cd pipelines/fraud-detection
python3 pipeline.py
# Check that compiled YAML uses the custom image
grep "image:" fraud_detection_pipeline.yaml
```

## Comparison with Tekton Image

| Feature | Tekton Image | KFP Component Image |
|---------|--------------|---------------------|
| **Purpose** | CI/CD tasks (lint, compile, execute) | Runtime pipeline components |
| **Registry** | `quay.io/alopezme/rhoai-experimentation-tekton` | `quay.io/alopezme/rhoai-experimentation-kfp` |
| **Python Version** | 3.11 | 3.12 |
| **KFP SDK** | ✅ Included | ❌ Not needed |
| **Linting Tools** | ✅ black, flake8, pylint | ❌ Not needed |
| **ML Libraries** | ✅ sklearn, pandas, numpy | ✅ sklearn, pandas, numpy |
| **ONNX** | ✅ onnx, skl2onnx | ✅ onnx, skl2onnx |
| **Infrastructure** | ✅ boto3, kubernetes | ✅ boto3, kubernetes |
| **Size** | ~1.5GB | ~600MB |

## Related Documentation

- [Main README](../README.md) - Project overview
- [Tekton Image README](../container-image/README.md) - CI/CD task image
- [Disconnected Optimization](../docs/notes/disconnected-optimization.md) - Air-gapped environment strategies

## License

GPL-3.0
