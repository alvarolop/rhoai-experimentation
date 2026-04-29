# Disconnected Environment Optimization

## Overview

This demo is optimized for **disconnected/air-gapped OpenShift environments** where internet access is restricted or unavailable. All dependencies are pre-packaged to minimize runtime overhead.

## Environment

- **OpenShift**: 4.20
- **Red Hat OpenShift AI**: 3.3.0
- **OpenShift Pipelines**: 1.15+
- **Deployment**: Fully disconnected (no external registry/package access)

## Optimization Strategy

### 1. Pre-built Custom Image

Instead of installing dependencies at runtime (`pip install`), we use a **custom builder image** with everything pre-installed:

**Base:** `registry.access.redhat.com/ubi9/python-311` (Red Hat UBI 9)

**Pre-installed packages:**
- `kfp==2.8.0` - Kubeflow Pipelines SDK
- `kfp.kubernetes==1.3.0` - Kubernetes integration
- `scikit-learn==1.5.0` - ML library
- `pandas==2.2.2` - Data manipulation
- `numpy==1.26.4` - Numerical computing
- `requests==2.32.3` - HTTP client
- `pylint==3.1.0` - Linter
- `flake8==7.0.0` - Code style checker
- `black==24.3.0` - Code formatter

**Benefits:**
- ⚡ **Fast execution** - No download/install time
- 📦 **Disconnected-ready** - Works offline
- 🔒 **Consistent** - Same packages every run
- 💾 **Smaller logs** - No pip install output

### 2. Single Execution Task

Consolidated `execute-ds-pipeline` task that:

1. **Compiles** the pipeline from Python
2. **Uploads** to DSP server via KFP Client
3. **Executes** the pipeline run
4. **Waits** for completion (configurable)
5. **Returns** run ID and status

**Old approach (3 tasks):**
```
lint → compile-upload → run
```

**New approach (2 tasks):**
```
lint → execute-pipeline
```

**Time savings:**
- Fewer container startups
- Shared Python context
- No intermediate artifacts

### 3. Native Kubernetes Authentication

Uses **ServiceAccount tokens** instead of external credentials:

```python
# Read from mounted ServiceAccount
with open('/var/run/secrets/kubernetes.io/serviceaccount/namespace') as f:
    namespace = f.read().strip()

with open('/var/run/secrets/kubernetes.io/serviceaccount/token') as f:
    token = f.read().strip()

# Use for DSP authentication
client = kfp.Client(
    host=f'https://ds-pipeline-dspa.{namespace}.svc:8443',
    existing_token=token,
    ssl_ca_cert='/var/run/secrets/kubernetes.io/serviceaccount/service-ca.crt'
)
```

**Benefits:**
- No external secrets management
- Automatic RBAC integration
- Works in disconnected clusters
- Leverages OpenShift security

### 4. Red Hat ClusterTasks

Uses **official ClusterTasks** from OpenShift Pipelines operator:

- `git-clone` - Maintained by Red Hat
- Automatically updated with operator
- No custom task maintenance needed

Fallback to custom tasks available if needed.

## Image Management for Disconnected

### Mirror Custom Builder Image

1. **Build locally or in connected environment:**

```bash
cd container-image
podman build -t quay.io/myorg/rhoai-kfp-builder:latest .
```

2. **Mirror to disconnected registry:**

```bash
# Export image
podman save quay.io/myorg/rhoai-kfp-builder:latest -o kfp-builder.tar

# Transfer tar to disconnected environment

# Import to disconnected registry
podman load -i kfp-builder.tar
podman tag quay.io/myorg/rhoai-kfp-builder:latest \
  registry.disconnected.local/rhoai/kfp-builder:latest
podman push registry.disconnected.local/rhoai/kfp-builder:latest
```

3. **Update Helm values:**

```yaml
tekton:
  image: registry.disconnected.local/rhoai/kfp-builder:latest
```

### Mirror Red Hat Images

Required Red Hat images (already in disconnected cluster if RHOAI is installed):

```
registry.access.redhat.com/ubi9/python-311
registry.redhat.io/openshift-pipelines/pipelines-git-init-rhel9:v1.15
```

These should be mirrored as part of standard OpenShift disconnected installation.

## Component Images (Kubeflow Pipelines)

Pipeline components also use pre-mirrored UBI9 image:

```python
@component(
    base_image="registry.access.redhat.com/ubi9/python-311",
    packages_to_install=["pandas==2.2.2", "numpy==1.26.4"]
)
```

**For disconnected:** The `packages_to_install` will be downloaded from PyPI mirror or pre-installed in component image.

### Option 1: Use Internal PyPI Mirror

Set up internal PyPI mirror (e.g., Artifactory, Nexus):

```python
@component(
    base_image="registry.disconnected.local/ubi9/python-311",
    packages_to_install=["pandas==2.2.2", "numpy==1.26.4"],
    pip_index_urls=["https://pypi.disconnected.local/simple"]
)
```

### Option 2: Pre-build Component Images

Create custom component images with packages pre-installed:

```dockerfile
FROM registry.access.redhat.com/ubi9/python-311

RUN pip install --no-cache-dir \
    pandas==2.2.2 \
    numpy==1.26.4 \
    scikit-learn==1.5.0

USER 1001
```

Use in components:

```python
@component(
    base_image="registry.disconnected.local/rhoai/ml-base:latest"
)
def my_component(...):
    import pandas as pd
    # packages already available
```

## Performance Comparison

### Old Approach (with pip install)

```
Task: execute-pipeline
├─ Install KFP SDK: ~45s
├─ Compile pipeline: ~5s
├─ Upload pipeline: ~2s
└─ Execute pipeline: ~1s
Total: ~53s + pipeline runtime
```

### New Approach (pre-installed)

```
Task: execute-pipeline
├─ Compile pipeline: ~5s
├─ Upload pipeline: ~2s
└─ Execute pipeline: ~1s
Total: ~8s + pipeline runtime
```

**Time saved: ~45 seconds per run** ⚡

## Network Requirements

### What needs network access:

**During build (connected environment):**
- Pull base images from Red Hat registries
- Install Python packages from PyPI

**During runtime (disconnected environment):**
- ✅ None - everything is pre-packaged
- Only internal cluster networking required

### Internal cluster networking:

```
Tekton Pod → DSP API Server (HTTPS, port 8443)
Pipeline Components → S3 Storage (MinIO/AWS S3)
Pipeline Components → Model Registry (HTTP, port 8080)
```

All communication stays within the cluster.

## Verification

Test that everything works disconnected:

```bash
# Verify custom image is in disconnected registry
oc get pod -l tekton.dev/task=execute-ds-pipeline -o yaml | grep image:

# Verify no external network calls
oc logs -l tekton.dev/task=execute-ds-pipeline | grep -i "download\|fetch\|install"
# Should be empty

# Check execution time
tkn taskrun describe <taskrun-name> | grep "Duration"
# Should be < 15s for execute-pipeline task
```

## Troubleshooting Disconnected Issues

### Image Pull Errors

**Symptom:**
```
Failed to pull image: connection refused / timeout
```

**Solution:**
1. Verify image exists in disconnected registry
2. Check imagePullSecrets are configured
3. Verify registry is reachable from cluster

### Package Installation Failures (Components)

**Symptom:**
```
Could not find a version that satisfies the requirement pandas==2.2.2
```

**Solutions:**
1. Set up internal PyPI mirror
2. Or pre-build component images with packages
3. Or include package files in pipeline artifacts

### DNS Resolution Issues

**Symptom:**
```
Could not resolve host: ds-pipeline-dspa.<namespace>.svc
```

**Solution:**
- Verify cluster DNS is working: `oc run test --image=busybox -- nslookup kubernetes`
- Check service exists: `oc get svc ds-pipeline-dspa`

## Best Practices

1. **Version pin everything** - Use exact versions for reproducibility
2. **Test in disconnected** - Validate before production deployment
3. **Monitor image sizes** - Keep custom images lean
4. **Document dependencies** - Track what's in custom images
5. **Automate image builds** - Use CI/CD for custom images
6. **Use SHA digests** - For critical base images (immutability)

## Related Documentation

- [Container Image README](../../container-image/README.md) - Building custom image
- [Using ClusterTasks](using-clustertasks.md) - Red Hat ClusterTasks
- [Architecture](../architecture.md) - System design

## References

- [OpenShift Disconnected Installation](https://docs.openshift.com/container-platform/4.20/installing/disconnected_install/index.html)
- [Red Hat OpenShift AI Documentation](https://access.redhat.com/documentation/en-us/red_hat_openshift_ai/3.3)
- [Mirroring Images for Disconnected](https://docs.openshift.com/container-platform/4.20/installing/disconnected_install/installing-mirroring-installation-images.html)
