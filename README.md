# RHOAI Pipelines Experimentation

Demonstration of OpenShift AI Data Science Pipelines capabilities through a complete fraud detection ML workflow: synthetic data generation, model training, model registry integration, KServe deployment, and performance benchmarking.

## Overview

This repository showcases:

- **Kubeflow Pipelines** - End-to-end ML workflow with 5 components
- **Tekton Automation** - CI/CD for pipeline deployment using OpenShift Pipelines
- **Model Registry** - Version tracking and metadata management
- **KServe Integration** - Model serving with InferenceService
- **Helm Deployment** - Declarative infrastructure as code
- **Red Hat Official Images** - Uses UBI9 and OpenShift Pipelines certified images

## Prerequisites

- OpenShift cluster with **Red Hat OpenShift AI 3.3.x** installed
- Namespace configured with:
  - DataSciencePipelines server running (KFP 2.5.0)
  - Model Registry server accessible
- **OpenShift Pipelines** operator installed (v1.15+)
- S3-compatible storage (MinIO or AWS S3)
- `oc` and `helm` CLI tools
- **Custom builder image** (see [Building the Image](#building-the-custom-image))

**Tested on:**
- OpenShift 4.20
- Red Hat OpenShift AI 3.3.0 / 3.3.2
- OpenShift Pipelines 1.15+

## Container Images

This demo uses **official Red Hat container images**:

- **Kubeflow Pipeline Components**: `registry.access.redhat.com/ubi9/python-311` (UBI 9)
- **Tekton Tasks**: Uses Red Hat OpenShift Pipelines ClusterTasks (git-clone)
- **Custom Builder**: Based on `registry.access.redhat.com/ubi9/python-311`

All images are:
- ✅ Certified and supported by Red Hat
- ✅ OpenShift-compatible (arbitrary user IDs)
- ✅ Security-scanned and updated regularly
- ✅ RHEL/UBI9-based for enterprise support

### ClusterTasks vs Custom Tasks

By default, this demo uses **Red Hat ClusterTasks** (maintained by Red Hat, installed with OpenShift Pipelines operator):

```yaml
tekton:
  useClusterTasks: true  # Recommended
```

Custom task definitions are also provided as fallback. See [Using ClusterTasks](docs/notes/using-clustertasks.md) for details.

## Quick Start

### 1. Build the Custom Image

Build and push the container image with pre-installed dependencies:

```bash
# Login to registry
podman login quay.io

# Build and push
cd container-image
IMAGE_NAME=quay.io/alopezme/rhoai-kfp-builder \
IMAGE_TAG=latest \
PUSH=true \
./build-image.sh
```

See [container-image/README.md](container-image/README.md) for details.

### 2. Install the Helm Chart

```bash
helm install fraud-detection chart/ \
  --set tekton.image=quay.io/alopezme/rhoai-kfp-builder:latest \
  --set s3.accessKeyId=<your-access-key> \
  --set s3.secretAccessKey=<your-secret-key> \
  --set s3.endpoint=<minio-endpoint> \
  --set namespace=<your-namespace>
```

This deploys:
- Tekton tasks and pipeline definitions
- PersistentVolumeClaim for workspace
- Secrets for S3 credentials
- ConfigMap with Kubeflow pipeline source code

### 3. Trigger the Tekton Pipeline

**Option A: Manual Trigger**

```bash
oc create -f tekton/example-run.yaml
```

**Option B: Webhook Trigger (Automated)**

Configure GitHub webhook to automatically trigger on push:

1. Get webhook URL:
```bash
oc get route kfp-webhook-listener -n <namespace> -o jsonpath='{.spec.host}'
```

2. Add webhook in GitHub repository settings:
   - **Payload URL**: `https://<route-host>`
   - **Secret**: Value from `tekton.triggers.webhookSecret`
   - **Events**: Push events

See [Tekton Triggers Setup](docs/notes/tekton-triggers-setup.md) for details.

### 4. Monitor Progress

```bash
# Watch Tekton pipeline
oc logs -f -n <your-namespace> -l tekton.dev/pipelineRun=fraud-detection-run

# Check Kubeflow pipeline in RHOAI UI
# Navigate to Data Science Pipelines → Runs
```

## Architecture

```
┌─────────────┐
│   Tekton    │  Lints → Compiles → Uploads → Triggers
│  Pipeline   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│          Kubeflow Pipeline (Data Science Pipelines)     │
│                                                           │
│  1. Generate Data → 2. Train Model → 3. Register Model  │
│         ↓                                                 │
│  4. Deploy Model → 5. Benchmark                          │
└──────────────┬──────────────────────────────────────────┘
               │
      ┌────────┴────────┐
      ▼                 ▼
┌──────────┐      ┌──────────┐
│  Model   │      │  KServe  │
│ Registry │      │Inference │
└──────────┘      └──────────┘
```

See [docs/architecture.md](docs/architecture.md) for detailed flow.

## Repository Structure

```
.
├── chart/                      # Helm chart for deployment
│   ├── templates/              # Kubernetes/Tekton resources
│   └── values.yaml             # Configuration
├── pipelines/
│   └── fraud-detection/        # Kubeflow pipeline
│       ├── pipeline.py         # Pipeline definition
│       └── components/         # Pipeline components
├── tekton/                     # Tekton examples
├── docs/                       # Documentation
│   ├── architecture.md
│   ├── kubeflow-pipelines-primer.md
│   └── notes/                  # Architectural decisions
└── README.md
```

## How It Works

### Kubeflow Pipeline

The fraud detection pipeline consists of 5 steps:

1. **Generate Synthetic Data** - Creates 10,000 transaction records with realistic fraud patterns (~2% fraud rate)
2. **Train Model** - Trains a RandomForestClassifier with class balancing
3. **Register Model** - Stores model metadata and artifacts in Model Registry
4. **Deploy Model** - Creates a KServe InferenceService with mlserver runtime
5. **Benchmark Model** - Measures inference latency (p50, p95, p99) and throughput

See [pipelines/fraud-detection/README.md](pipelines/fraud-detection/README.md) for component details.

### Tekton Automation

The Tekton pipeline automates deployment with optimized tasks:

1. **Git Clone** - Clones repository using Red Hat ClusterTask
2. **Lint** - Validates code with Black, flake8, and pylint (pre-installed)
3. **Execute Pipeline** - Compiles, uploads, and runs DSP pipeline (waits for completion)

**Key optimizations for disconnected environments:**
- Uses custom builder image with all dependencies pre-installed
- No pip installs during execution (fast startup)
- Native Kubernetes authentication (ServiceAccount tokens)
- Single consolidated task for pipeline execution

See [tekton/README.md](tekton/README.md) for usage.

## Customization

### Modify Pipeline Parameters

Edit `chart/values.yaml`:

```yaml
kfpPipeline:
  name: my-custom-pipeline
  # ... other settings
```

Or override during install:

```bash
helm install fraud-detection chart/ \
  --set kfpPipeline.name=my-pipeline
```

### Change Model Algorithm

Edit `pipelines/fraud-detection/components/train_model.py`:

```python
from sklearn.linear_model import LogisticRegression

clf = LogisticRegression()
```

### Add Pipeline Components

1. Create a new component in `pipelines/fraud-detection/components/`
2. Import and use in `pipeline.py`
3. Update Helm chart if new dependencies are needed

## Related Repositories

- [rhoai-gitops](https://github.com/alvarolop/rhoai-gitops) - RHOAI installation and GitOps automation
- [rhoai-serving](https://github.com/alvarolop/rhoai-serving) - Model serving with KServe

## Learning Resources

- [Kubeflow Pipelines Primer](docs/kubeflow-pipelines-primer.md) - Introduction to KFP concepts
- [Architecture Details](docs/architecture.md) - Deep dive into the system design
- [Using ClusterTasks](docs/notes/using-clustertasks.md) - Red Hat ClusterTasks vs custom tasks

## Troubleshooting

### Tekton Pipeline Fails

```bash
# List pipeline runs
oc get pipelinerun -n <namespace>

# Check logs
oc logs -n <namespace> -l tekton.dev/pipelineRun=<pipelinerun-name> --all-containers

# Common issues:
# - Syntax errors in pipeline.py → check lint output
# - Missing dependencies → verify requirements.txt
# - DSP API unreachable → check dsp.apiUrl in values.yaml
```

### Kubeflow Pipeline Fails

```bash
# View in RHOAI UI or check pod logs
oc logs -n <namespace> <pod-name>

# Common issues:
# - S3 credentials incorrect → verify secrets
# - Model Registry unavailable → check modelRegistry.url
# - Resource limits → adjust in component definitions
```

## License

GPL-3.0
