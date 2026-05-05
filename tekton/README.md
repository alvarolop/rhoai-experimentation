# Tekton Automation for KFP Pipelines

This directory contains PipelineRun examples for deploying and executing Kubeflow pipelines using Tekton (OpenShift Pipelines).

## Overview

The Tekton automation is split into two separate pipelines:

### 1. CI/CD Pipeline (`ci-kfp-pipeline`)

**Purpose**: Validate and upload pipeline definitions  
**Trigger**: Code changes (git webhook or manual)  
**File**: `ci-kfp-pipelinerun.yaml`

**Workflow**:
1. Clone git repository
2. Lint Python code (Black, flake8, pylint)
3. Compile KFP pipeline to YAML
4. **Upload pipeline definition** to DSP (NOT a run)

**Result**: Pipeline available in RHOAI UI for execution

### 2. Execution Pipeline (`run-kfp-pipeline`)

**Purpose**: Create runs from existing pipeline definitions  
**Trigger**: Manual, schedule, or external trigger  
**File**: `run-kfp-pipelinerun.yaml`

**Workflow**:
1. Lookup existing pipeline by name
2. Create a new run with parameters
3. Optionally wait for completion

**Result**: KFP pipeline run executing in RHOAI

### 3. Legacy Pipeline (Deprecated)

**File**: `legacy-pipelinerun.yaml`

The old all-in-one pipeline that does everything in one run. Prefer using the split approach above.

## Files

| File | Pipeline | Description |
|------|----------|-------------|
| `ci-kfp-pipelinerun.yaml` | CI/CD | Upload pipeline definition (use when code changes) |
| `run-kfp-pipelinerun.yaml` | Execution | Create run from existing pipeline (use to train/execute) |
| `example-run.yaml` | CI/CD | Same as `ci-kfp-pipelinerun.yaml` (default example) |
| `legacy-pipelinerun.yaml` | Legacy | Old all-in-one pipeline (deprecated) |

## Quick Start

### Step 1: Upload Pipeline Definition

**When to use**: When pipeline code changes (new features, bug fixes, first deployment)

```bash
oc create -f tekton/ci-kfp-pipelinerun.yaml
```

Or use the example:

```bash
oc create -f tekton/example-run.yaml
```

**Monitor**:

```bash
tkn pipelinerun logs -f -n rhoai-playground $(tkn pr list -n rhoai-playground --limit 1 -o name)
```

**Result**: Pipeline definition `fraud-detection-pipeline` uploaded to DSP

### Step 2: Execute Pipeline

**When to use**: When you want to train a model, process data, run the pipeline

**Default parameters**:

```bash
oc create -f tekton/run-kfp-pipelinerun.yaml
```

**Custom parameters**:

```bash
cat <<EOF | oc create -f -
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  generateName: run-kfp-pipeline-
  namespace: rhoai-playground
spec:
  pipelineRef:
    name: run-kfp-pipeline
  params:
    - name: pipeline-name
      value: fraud-detection-pipeline
    - name: experiment-name
      value: fraud-detection-experiments
    - name: parameters
      value: '{"num_samples": 20000, "n_estimators": 200, "fraud_ratio": 0.03}'
    - name: wait-for-completion
      value: "true"
EOF
```

**Monitor**:

```bash
tkn pipelinerun logs -f -n rhoai-playground $(tkn pr list -n rhoai-playground --limit 1 -o name)
```

## Common Workflows

### Development Workflow

```bash
# 1. Make code changes to pipelines/fraud-detection/

# 2. Upload new pipeline definition
oc create -f tekton/ci-kfp-pipelinerun.yaml

# 3. Execute the pipeline
oc create -f tekton/run-kfp-pipelinerun.yaml
```

### Production Workflow

```bash
# CI/CD: Upload pipeline on git push (webhook trigger)
# Execution: CronJob or manual trigger

# Example: Daily execution at 2 AM
cat <<EOF | oc create -f -
apiVersion: batch/v1
kind: CronJob
metadata:
  name: fraud-detection-daily
  namespace: rhoai-playground
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: pipeline
          containers:
          - name: create-run
            image: quay.io/openshift/origin-cli:latest
            command: ["/bin/bash", "-c"]
            args:
            - |
              oc create -f - <<YAML
              apiVersion: tekton.dev/v1
              kind: PipelineRun
              metadata:
                generateName: run-kfp-pipeline-
              spec:
                pipelineRef:
                  name: run-kfp-pipeline
                params:
                  - name: pipeline-name
                    value: fraud-detection-pipeline
              YAML
          restartPolicy: Never
EOF
```

### Experimentation Workflow

```bash
# Upload pipeline once
oc create -f tekton/ci-kfp-pipelinerun.yaml

# Run with different parameters
for estimators in 50 100 200; do
  cat <<EOF | oc create -f -
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  generateName: run-kfp-pipeline-
  namespace: rhoai-playground
spec:
  pipelineRef:
    name: run-kfp-pipeline
  params:
    - name: pipeline-name
      value: fraud-detection-pipeline
    - name: experiment-name
      value: hyperparameter-tuning
    - name: run-name
      value: "estimators-${estimators}"
    - name: parameters
      value: '{"n_estimators": ${estimators}}'
EOF
done
```

## Parameters

### CI/CD Pipeline Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `git-url` | Git repository URL | `https://github.com/alvarolop/rhoai-experimentation.git` |
| `git-revision` | Branch/tag/SHA to clone | `main` |
| `pipeline-path` | Path to pipeline in repo | `pipelines/fraud-detection` |
| `pipeline-name` | Name for the pipeline | `fraud-detection-pipeline` |
| `pipeline-file` | Python file to compile | `pipeline.py` |
| `pipeline-description` | Description for the pipeline | `"Fraud Detection ML Pipeline..."` |

### Execution Pipeline Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `pipeline-name` | Existing pipeline to run | `fraud-detection-pipeline` |
| `experiment-name` | Experiment to organize runs | `fraud-detection-experiments` |
| `run-name` | Name for this run | `""` (auto-generated) |
| `parameters` | JSON pipeline parameters | `"{}"` |
| `wait-for-completion` | Wait for run to finish | `"true"` |
| `timeout` | Timeout in seconds | `"3600"` |

## Monitoring

### List all pipeline runs

```bash
# Tekton pipeline runs
tkn pipelinerun list -n rhoai-playground

# KFP pipeline runs (via CLI)
oc get workflows -n rhoai-playground
```

### View logs

```bash
# Tekton pipeline logs
tkn pipelinerun logs ci-kfp-pipeline-run-xxxxx -f -n rhoai-playground
tkn pipelinerun logs run-kfp-pipeline-xxxxx -f -n rhoai-playground

# Or use kubectl
oc logs -f -n rhoai-playground -l tekton.dev/pipelineRun=<run-name> --all-containers
```

### OpenShift Console

- **Tekton**: Pipelines → PipelineRuns
- **KFP**: Data Science Pipelines → Runs

## Git Authentication

For private repositories, uncomment the workspace in the PipelineRun:

**SSH Authentication:**

```yaml
workspaces:
  - name: shared-workspace
    volumeClaimTemplate: ...
  - name: git-ssh-credentials
    secret:
      secretName: git-auth-ssh
```

**Basic Authentication:**

```yaml
workspaces:
  - name: shared-workspace
    volumeClaimTemplate: ...
  - name: git-basic-credentials
    secret:
      secretName: git-auth-basic
```

See [Azure DevOps Git Authentication Guide](../docs/azure-devops-git-auth.md) for detailed setup.

## Troubleshooting

### Pipeline not found error

```
ERROR: Pipeline not found: fraud-detection-pipeline
```

**Solution**: Run the CI/CD pipeline first to upload the definition:

```bash
oc create -f tekton/ci-kfp-pipelinerun.yaml
```

### Lint failures

```
ERROR: Code not formatted
```

**Solution**: Run Black locally before pushing:

```bash
black pipelines/fraud-detection/
```

### Git authentication failures

```
ERROR: Repository not found
```

**Solution**: Configure git authentication secrets. See [docs/azure-devops-git-auth.md](../docs/azure-devops-git-auth.md)

## Requirements

- OpenShift Pipelines operator v1.15+
- RHOAI with Data Science Pipelines enabled
- ServiceAccount `pipeline` with permissions to:
  - Create/read PVCs
  - Access DSP API
  - Create/manage workflows

## Related Documentation

- [Helm Chart README](../chart/README.md) - Full deployment guide
- [Git Authentication](../docs/azure-devops-git-auth.md) - Private repo setup
- [Using Red Hat Tasks](../docs/notes/using-red-hat-tasks.md) - Task resolver details
