# Kubeflow Pipelines Primer

A concise introduction to Kubeflow Pipelines in the context of Red Hat OpenShift AI.

## What are Kubeflow Pipelines?

Kubeflow Pipelines (KFP) is an open-source platform for building and deploying portable, scalable machine learning workflows. In OpenShift AI, it's provided as **Data Science Pipelines (DSP)**, a managed service that runs Kubeflow pipelines on OpenShift.

## Key Concepts

### Pipeline

A **pipeline** is a directed acyclic graph (DAG) of ML workflow steps. Each node is a component, edges represent data dependencies.

Example:
```
Data → Preprocess → Train → Evaluate → Deploy
```

### Component

A **component** is a self-contained piece of code (typically a Python function) that performs one step. Components:
- Run in containers
- Accept inputs (parameters, artifacts)
- Produce outputs (artifacts, metrics)
- Are reusable across pipelines

### Artifact

An **artifact** is data passed between components. Types:
- `Dataset` - Tabular data, CSVs
- `Model` - ML model files (pickle, ONNX, SavedModel)
- `Metrics` - Numerical metrics for tracking
- `Artifact` - Generic file/data

Artifacts are stored in S3-compatible storage and referenced by URI.

### Run

A **run** is a single execution of a pipeline with specific parameter values. Runs can be:
- Triggered manually via UI
- Scheduled (cron-like)
- Triggered via API (as in this repo's Tekton pipeline)

## How Data Science Pipelines Works in RHOAI

1. **Author:** Write pipeline in Python using KFP SDK
2. **Compile:** Convert Python to YAML specification
3. **Upload:** Submit YAML to DSP server via UI or API
4. **Execute:** DSP server orchestrates component containers on OpenShift
5. **Monitor:** View run status, logs, artifacts in RHOAI dashboard

## Component Patterns

### Function-Based Component

```python
from kfp.dsl import component, Output, Dataset

@component(
    base_image="python:3.11-slim",
    packages_to_install=["pandas"]
)
def my_component(
    param: str,
    output_data: Output[Dataset]
):
    import pandas as pd
    df = pd.DataFrame({"col": [param]})
    df.to_csv(output_data.path, index=False)
```

KFP SDK automatically:
- Builds a container image
- Installs packages
- Handles artifact I/O

### Connecting Components

```python
from kfp import dsl

@dsl.pipeline(name="My Pipeline")
def my_pipeline():
    task1 = component_a()
    task2 = component_b(input_data=task1.outputs['output_data'])
```

Outputs from `task1` become inputs to `task2` - DSP handles data passing.

## Data Science Pipelines vs. Tekton

| Feature | Data Science Pipelines | Tekton |
|---------|------------------------|--------|
| **Purpose** | ML workflows | General CI/CD |
| **Optimized for** | Data scientists | DevOps engineers |
| **Artifacts** | Models, datasets, metrics | Build artifacts, images |
| **UI** | RHOAI dashboard | OpenShift Pipelines console |
| **Use case** | Train, evaluate, deploy models | Deploy code, run tests |

**In this repo:**
- **Tekton** deploys the Kubeflow pipeline definition (CI/CD)
- **KFP/DSP** runs the ML workflow (training, serving)

## Benefits of Pipelines

1. **Reproducibility** - Same code + data = same results
2. **Versioning** - Track pipeline versions, compare runs
3. **Collaboration** - Share pipelines across teams
4. **Automation** - Schedule or trigger runs programmatically
5. **Observability** - Logs, metrics, artifacts in one place
6. **Scalability** - Kubernetes handles resource allocation

## Common Workflow

```
┌─────────────┐
│ Data Prep   │  Load, clean, feature engineering
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Training  │  Model training, hyperparameter tuning
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Evaluation  │  Metrics, validation, model comparison
└──────┬──────┘
       │
       ▼
┌─────────────┐
│Registration │  Save to Model Registry
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Deployment  │  Deploy to KServe, batch inference
└─────────────┘
```

This is exactly what the fraud detection pipeline implements.

## Further Reading

- [Kubeflow Pipelines Documentation](https://www.kubeflow.org/docs/components/pipelines/)
- [Red Hat OpenShift AI Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed)
- [KFP SDK Reference](https://kubeflow-pipelines.readthedocs.io/)

## Integration with RHOAI

Data Science Pipelines integrates with:

- **Model Registry** - Version and track models
- **KServe** - Deploy models from pipelines
- **Jupyter Notebooks** - Author pipelines interactively
- **S3 Storage** - Artifact persistence (MinIO, AWS S3, ODF)
- **OpenShift** - RBAC, monitoring, storage classes
