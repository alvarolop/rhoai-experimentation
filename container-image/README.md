# Tekton Builder Image

Custom container image for **Tekton CI/CD tasks** in disconnected/air-gapped OpenShift environments.

## Purpose

This image is **exclusively for Tekton tasks** that compile and execute Kubeflow Pipelines:
- ✅ **Lint Task** (`lint-python`) - Code quality checks with Black, flake8, pylint
- ✅ **Execute Pipeline Task** (`execute-ds-pipeline`) - Compile and run KFP pipelines

**Important:** This image is **NOT** used by Kubeflow pipeline components. Components use their own base images specified in the `@component` decorator with `packages_to_install`.

## Why a Custom Image?

### Disconnected Environment Requirements

In disconnected/air-gapped environments:
- ❌ **Cannot run `pip install` during task execution** (no PyPI access)
- ❌ **Cannot use base Python images** (missing required packages)
- ✅ **Must pre-install all dependencies** at image build time

### Why Not Use RHOAI Workbench Images?

Red Hat OpenShift AI 3.3 workbench images include KFP SDK and ML libraries but:
- ❌ **No linting tools** (Black, flake8, pylint) - not needed for notebooks
- ❌ **~2GB size** - includes full JupyterLab environment
- ❌ **Python 3.12** - KFP 2.14.1 requires Python 3.11

### Our Custom Image

- ✅ **Python 3.11** - Required for KFP 2.14.1 compatibility
- ✅ **Linting tools** - Black, flake8, pylint pre-installed
- ✅ **KFP SDK** - kfp 2.14.1, kfp-kubernetes 1.3.0
- ✅ **ML libraries** - scikit-learn, pandas, numpy, boto3, kubernetes client
- ✅ **Smaller size (~500MB)** - No Jupyter overhead
- ✅ **Disconnected-ready** - Zero pip installs at runtime
- ✅ **Fast startup** - All dependencies pre-baked

## Image Contents

### Base Image

`registry.access.redhat.com/ubi9/python-311` (Red Hat Universal Base Image 9)

### System Tools

- git (for repository operations)

### Python Packages

**Tekton CI/CD Tools:**
- `kfp==2.14.1` - Kubeflow Pipelines SDK (pipeline compilation and execution)
- `kfp-kubernetes==1.3.0` - Kubernetes integration for KFP
- `black==24.10.0` - Code formatter
- `flake8==7.1.1` - Code style checker
- `pylint==3.3.1` - Python linter

**ML and Data Science Libraries** (for pipeline component compatibility):
- `scikit-learn==1.7.0` - Machine learning
- `pandas==2.3.0` - Data manipulation
- `numpy==2.3.0` - Numerical computing
- `skl2onnx==1.18.0` - ONNX model conversion
- `onnx==1.17.0` - ONNX format support

**Infrastructure Clients:**
- `boto3==1.37.0` - AWS S3 client (MinIO compatible)
- `kubernetes==31.0.0` - Kubernetes API client
- `requests==2.32.3` - HTTP client

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
cd container-image

# Login to registry
podman login quay.io

# Build and push
IMAGE_NAME=quay.io/alopezme/rhoai-experimentation-tekton \
IMAGE_TAG=latest \
PUSH=true \
./build-image.sh
```

### Build Locally (No Push)

```bash
cd container-image
./build-image.sh
```

Output:
```
Building container image...
  Image: quay.io/alopezme/rhoai-experimentation-tekton:latest
  Push: false
...
Image built successfully
```

### Build with Custom Tag

```bash
cd container-image
IMAGE_NAME=quay.io/alopezme/rhoai-experimentation-tekton \
IMAGE_TAG=v1.0.0 \
PUSH=true \
./build-image.sh
```

### Manual Build with Podman

```bash
cd container-image

# Build
podman build -f Containerfile -t quay.io/alopezme/rhoai-experimentation-tekton:latest .

# Push
podman push quay.io/alopezme/rhoai-experimentation-tekton:latest
```

## Using the Image

### Update Helm Values

Edit `chart/values.yaml`:

```yaml
tekton:
  image: quay.io/alopezme/rhoai-experimentation-tekton:v1.0.0
```

### Override During Install

```bash
helm install fraud-detection chart/ \
  --set tekton.image=quay.io/alopezme/rhoai-experimentation-tekton:v1.0.0 \
  --set s3.accessKeyId=<key> \
  --set s3.secretAccessKey=<secret>
```

### Verify Image in Tasks

After Helm install, check the tasks use the custom image:

```bash
# Check lint-python task
oc get task lint-python -n <namespace> -o jsonpath='{.spec.steps[0].image}'
# Output: quay.io/alopezme/rhoai-experimentation-tekton:latest

# Check execute-ds-pipeline task
oc get task execute-ds-pipeline -n <namespace> -o jsonpath='{.spec.steps[0].image}'
# Output: quay.io/alopezme/rhoai-experimentation-tekton:latest
```

## Automated Builds (GitHub Actions)

**✅ Configured** in `.github/workflows/build-push-image.yaml`

The workflow automatically:
- Triggers on changes to `container-image/Containerfile`
- Builds multi-arch (amd64 + arm64)
- Pushes to Quay.io
- Tags with `latest`, commit SHA, and semantic versions

### Setup GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

1. `QUAY_REPO_USERNAME` - Your Quay.io username or robot account name
2. `QUAY_REPO_TOKEN` - Quay.io password or robot token

### Manual Trigger

```bash
# Via GitHub UI
Actions → Build and Push Container Image → Run workflow

# Or push a tag
git tag v1.0.0
git push origin v1.0.0
```

## Disconnected Environment Workflow

### 1. Build in Connected Environment

```bash
podman build -f Containerfile -t quay.io/alopezme/rhoai-experimentation-tekton:v1.0.0 .
podman push quay.io/alopezme/rhoai-experimentation-tekton:v1.0.0
```

### 2. Mirror to Disconnected Registry

```bash
# From connected environment, mirror to disconnected registry
skopeo copy \
  docker://quay.io/alopezme/rhoai-experimentation-tekton:v1.0.0 \
  docker://registry.disconnected.local/rhoai/tekton-builder:v1.0.0
```

### 3. Use in Disconnected Cluster

```bash
helm install fraud-detection chart/ \
  --set tekton.image=registry.disconnected.local/rhoai/tekton-builder:v1.0.0
```

## Updating Dependencies

When updating Python packages or versions:

### 1. Update Containerfile

Edit `container-image/Containerfile`:

```dockerfile
RUN pip install --no-cache-dir \
    kfp==2.15.0 \  # Updated version
    ...
```

### 2. Rebuild and Push

```bash
cd container-image
IMAGE_TAG=v1.1.0 PUSH=true ./build-image.sh
```

### 3. Update Helm Chart

```bash
helm upgrade fraud-detection chart/ \
  --set tekton.image=quay.io/alopezme/rhoai-experimentation-tekton:v1.1.0
```

## Performance Benefits

### Without Custom Image (Base Python + pip install)

```
Task execution time:
├── Pull base image: ~10s
├── pip install kfp: ~60s
├── pip install linting tools: ~30s
├── Actual task work: ~20s
└── Total: ~120s
```

### With Custom Image (Pre-installed)

```
Task execution time:
├── Pull custom image: ~15s (first time only, then cached)
├── Actual task work: ~20s
└── Total: ~35s
```

**Savings:** ~85 seconds per task run (~70% faster)

## Image Size

Approximate size: **~500MB**

Breakdown:
- UBI9 Python 3.11 base: ~180MB
- System packages (git): ~20MB
- Python packages: ~300MB

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

### Import Errors in Tasks

**Error:**
```
ModuleNotFoundError: No module named 'kfp'
```

**Solutions:**

1. Verify image is being used:
   ```bash
   oc get task execute-ds-pipeline -o jsonpath='{.spec.steps[0].image}'
   ```

2. Check image exists and is pullable:
   ```bash
   podman pull quay.io/alopezme/rhoai-experimentation-tekton:latest
   ```

3. Verify packages are installed in image:
   ```bash
   podman run --rm quay.io/alopezme/rhoai-experimentation-tekton:latest pip list | grep kfp
   ```

### Version Conflicts

If Kubeflow components fail with dependency errors, remember:
- ✅ **Tekton tasks** use this custom image
- ✅ **Kubeflow components** use their own base images (specified in `@component` decorator)
- ❌ Don't try to use this image for Kubeflow components

### Build Failures

**Common issues:**

1. **Network timeout during pip install:**
   ```bash
   # Retry with increased timeout
   podman build --timeout 1200 -f Containerfile -t ...
   ```

2. **Out of disk space:**
   ```bash
   podman system prune -a
   ```

3. **Registry authentication:**
   ```bash
   podman login quay.io
   ```

## Testing the Image

### Test Locally

```bash
# Run container
podman run -it --rm quay.io/alopezme/rhoai-experimentation-tekton:latest bash

# Inside container, verify packages
python3 -c "import kfp; print(f'KFP: {kfp.__version__}')"
python3 -c "import black; print('Black installed')"
python3 -c "import sklearn; print(f'scikit-learn: {sklearn.__version__}')"
python3 -c "import boto3; print('boto3 installed')"
```

### Test in OpenShift

```bash
# Run test pod
oc run test-builder \
  --image=quay.io/alopezme/rhoai-experimentation-tekton:latest \
  --rm -it -- bash

# Inside pod
pip list | grep kfp
python3 -c "import kfp; print(kfp.__version__)"
```

## Image Variants

### Minimal (Smaller Size)

Remove unused packages for specific use cases:

```dockerfile
# Only KFP tools (no ML libraries)
RUN pip install --no-cache-dir \
    kfp==2.14.1 \
    kfp-kubernetes==1.3.0 \
    black==24.10.0 \
    flake8==7.1.1 \
    pylint==3.3.1
```

Estimated size: **~300MB**

### With Additional Tools

Add more packages if needed:

```dockerfile
RUN pip install --no-cache-dir \
    # Existing packages...
    jupyter==1.0.0 \
    pytest==8.0.0
```

## Related Documentation

- [Main README](../README.md) - Project overview
- [Disconnected Optimization](../docs/notes/disconnected-optimization.md) - Air-gapped environment strategies
- [GitHub Actions Workflow](../.github/workflows/README.md) - CI/CD automation

## License

GPL-3.0
