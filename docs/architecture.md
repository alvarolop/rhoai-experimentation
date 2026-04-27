# Architecture

This document describes the architecture and workflow of the RHOAI pipelines experimentation repository.

## System Components

### 1. Tekton Pipeline (Automation Layer)

**Purpose:** Automates the deployment and execution of Kubeflow pipelines

**Components:**
- **Tasks:** Atomic units of work (lint, compile, upload, run)
- **Pipeline:** Orchestrates tasks in sequence
- **PipelineRun:** Instance of pipeline execution
- **Workspace:** Shared storage (PVC) for pipeline artifacts

**Why Tekton?**
- Native to OpenShift (included in OpenShift Pipelines operator)
- Kubernetes-native CI/CD
- No external dependencies
- Integrated with OpenShift console

### 2. Kubeflow Pipeline (ML Workflow Layer)

**Purpose:** Defines the ML workflow from data to deployed model

**Components:**
- **Pipeline:** DAG of components with dependencies
- **Components:** Containerized steps (Python functions)
- **Artifacts:** Data passed between components (Dataset, Model, Metrics)
- **Data Science Pipelines Server:** RHOAI's managed Kubeflow backend

**Component Flow:**

```
┌──────────────────┐
│  Generate Data   │  Outputs: CSV Dataset
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Train Model    │  Inputs: Dataset
└────────┬─────────┘  Outputs: Model (pickle), Metrics
         │
         ▼
┌──────────────────┐
│ Register Model   │  Inputs: Model
└────────┬─────────┘  Outputs: Registry metadata
         │
         ▼
┌──────────────────┐
│  Deploy Model    │  Inputs: Registry metadata
└────────┬─────────┘  Outputs: Endpoint URL
         │
         ▼
┌──────────────────┐
│ Benchmark Model  │  Inputs: Endpoint URL
└──────────────────┘  Outputs: Performance metrics
```

### 3. Model Registry

**Purpose:** Version control and metadata tracking for ML models

**Features:**
- Model versioning
- Metadata storage (metrics, framework, algorithm)
- Artifact URIs
- Lineage tracking

**Integration:** Components write to registry via API, deployment reads model URIs

### 4. KServe (Serving Layer)

**Purpose:** Production model serving with autoscaling and monitoring

**Components:**
- **ServingRuntime:** Defines the serving framework (mlserver for scikit-learn)
- **InferenceService:** Model deployment specification
- **Predictor:** Actual serving pods

**Endpoint Pattern:**
```
http://<inference-service>-predictor.<namespace>.svc.cluster.local/v2/models/<name>/infer
```

## Workflow

### Phase 1: Deployment (Tekton)

1. User runs `helm install` → Kubernetes resources created
2. User triggers `PipelineRun` → Tekton starts
3. **Lint Task:**
   - Mounts pipeline source from ConfigMap/PVC
   - Runs `python -m py_compile`
   - Fails pipeline if syntax errors found
4. **Compile & Upload Task:**
   - Installs KFP SDK
   - Runs `kfp.compiler.Compiler().compile()`
   - Uploads YAML to DSP API
   - Returns pipeline ID
5. **Run Task:**
   - Uses pipeline ID to trigger execution
   - Creates pipeline run via DSP API
   - Returns run ID

### Phase 2: Execution (Kubeflow)

1. **Data Generation Component:**
   - Container starts (python:3.11-slim)
   - Generates synthetic fraud data
   - Writes CSV to artifact storage (S3)
   - Artifact reference passed to next component

2. **Training Component:**
   - Reads CSV from artifact storage
   - Trains RandomForestClassifier
   - Logs metrics (accuracy, precision, recall, F1)
   - Pickles model to artifact storage
   - Passes model artifact to registry component

3. **Registry Component:**
   - Reads model artifact
   - POSTs metadata to Model Registry API
   - Creates versioned model entry
   - Outputs registry ID and model URI

4. **Deployment Component:**
   - Reads registry metadata
   - Generates InferenceService YAML (or uses Kubernetes client)
   - Applies to cluster
   - Waits for model to be ready
   - Outputs inference endpoint URL

5. **Benchmark Component:**
   - Reads endpoint URL
   - Sends test inference requests
   - Measures latency percentiles (p50, p95, p99)
   - Calculates throughput
   - Logs performance metrics

### Phase 3: Monitoring

Users monitor via:
- **Tekton:** OpenShift Pipelines UI or `tkn` CLI
- **Kubeflow:** RHOAI Data Science Pipelines dashboard
- **KServe:** OpenShift console, Prometheus metrics

## Data Flow

```
┌──────────────┐
│ Helm Chart   │
│ (values.yaml)│
└──────┬───────┘
       │
       ▼
┌──────────────────────────┐
│  Kubernetes Resources    │
│  - Secrets (S3 creds)    │
│  - PVC (workspace)       │
│  - ConfigMap (pipeline)  │
│  - Tekton Tasks/Pipeline │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│   PipelineRun Trigger    │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ Tekton Execution         │
│  (lint → compile → run)  │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ KFP Pipeline Execution   │
│ (5 components in DAG)    │
└──────┬───────────────────┘
       │
       ▼
┌─────────────┬────────────┐
│             │            │
▼             ▼            ▼
Model       KServe    Metrics/Logs
Registry    Endpoint  (RHOAI UI)
```

## Design Decisions

### Why Function-Based Components?

- Simpler than containerized components
- KFP SDK handles containerization
- Easier to develop and test locally
- Dependencies declared inline

### Why Synthetic Data?

- No external dependencies
- Reproducible
- No licensing concerns
- Runs anywhere (no internet required)

### Why Tekton for Automation?

- Free with OpenShift subscriptions
- Native Kubernetes CRDs
- Well-integrated with OpenShift console
- Alternative to Jenkins/GitLab CI for K8s-native workflows

### Why Separate Tekton and Kubeflow Pipelines?

- **Tekton:** CI/CD for deploying pipeline definitions
- **Kubeflow:** ML workflow orchestration
- Separation of concerns: infrastructure vs. ML logic
- Tekton runs once to deploy, Kubeflow runs many times for training

## Security Considerations

- S3 credentials stored in Kubernetes Secrets
- ServiceAccount RBAC limits Tekton permissions
- Model Registry API should use authentication (configured in RHOAI)
- InferenceService endpoints exposed internally by default

## Scalability

**Horizontal:**
- Multiple pipeline runs can execute concurrently
- KServe autoscales based on load
- Tekton tasks run in parallel where possible

**Vertical:**
- Component resource requests/limits configurable
- Pipeline can be modified for distributed training
- Model sharding possible with KServe

## Extension Points

1. **Add new pipeline components** - Extend the ML workflow
2. **Custom Tekton tasks** - Add testing, security scanning
3. **Multiple pipelines** - Add more use cases beyond fraud detection
4. **GitOps integration** - ArgoCD to sync pipeline definitions
5. **Monitoring** - Prometheus metrics, custom dashboards
