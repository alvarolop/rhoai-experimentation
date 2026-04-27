# Tekton Automation

This directory contains resources for automating Kubeflow pipeline deployment using Tekton (OpenShift Pipelines).

## Overview

The Tekton pipeline automates the following workflow:

1. **Lint** - Validates Python syntax of the Kubeflow pipeline
2. **Compile & Upload** - Compiles the pipeline to YAML and uploads to Data Science Pipelines
3. **Run** - Triggers execution of the Kubeflow pipeline

## Pipeline Components

### Tasks

- `lint-kfp-pipeline` - Validates pipeline Python code syntax
- `compile-upload-kfp` - Installs dependencies, compiles, and uploads the pipeline
- `run-kfp-pipeline` - Triggers a pipeline run on the DSP server

### Pipeline

`deploy-kfp-pipeline` - Orchestrates the three tasks sequentially

## Usage

### Deploy via Helm

The Tekton resources are automatically deployed when you install the Helm chart:

```bash
helm install fraud-detection chart/ \
  --set s3.accessKeyId=<your-key> \
  --set s3.secretAccessKey=<your-secret>
```

### Trigger a Pipeline Run

**Manual Trigger:**

```bash
oc create -f tekton/example-run.yaml
```

Or create directly:

```bash
cat <<EOF | oc create -f -
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  generateName: fraud-detection-run-
  namespace: rhoai-pipelines-demo
spec:
  pipelineRef:
    name: deploy-kfp-pipeline
  params:
    - name: git-url
      value: https://github.com/alvarolop/rhoai-experimentation.git
    - name: git-revision
      value: main
    - name: pipeline-path
      value: pipelines/fraud-detection
    - name: pipeline-name
      value: fraud-detection-pipeline
    - name: dsp-api-url
      value: http://ds-pipeline-dspa.rhoai-pipelines-demo.svc.cluster.local:8888
  workspaces:
    - name: shared-workspace
      persistentVolumeClaim:
        claimName: pipeline-workspace
EOF
```

**Automated Trigger (Webhook):**

Get the webhook URL:
```bash
oc get route kfp-webhook-listener -n rhoai-pipelines-demo -o jsonpath='{.spec.host}'
```

Configure in GitHub:
- Repository → Settings → Webhooks → Add webhook
- Payload URL: `https://<route-host>`
- Content type: `application/json`
- Secret: Value from Helm chart (`tekton.triggers.webhookSecret`)
- Events: Push

See [../docs/notes/tekton-triggers-setup.md](../docs/notes/tekton-triggers-setup.md) for detailed setup.

### Monitor Progress

```bash
# List pipeline runs
oc get pipelinerun -n rhoai-pipelines-demo

# View logs (follow all containers)
oc logs -f -n rhoai-pipelines-demo -l tekton.dev/pipelineRun=<run-name> --all-containers

# Or watch in OpenShift console
# Pipelines → PipelineRuns
```

## Parameters

The Tekton pipeline accepts these parameters:

- `pipeline-name` - Name of the Kubeflow pipeline (default: fraud-detection-pipeline)
- `pipeline-file` - Python file to compile (default: pipeline.py)
- `dsp-api-url` - Data Science Pipelines API endpoint
- `namespace` - Target namespace for deployment

## Requirements

- OpenShift Pipelines operator installed
- ServiceAccount with permissions to:
  - Read/write PVCs
  - Access Data Science Pipelines API
  - Create InferenceServices (if deploying models)

## Failure Handling

The pipeline fails fast:

- **Lint failures** - Pipeline stops if syntax errors are found
- **Compile failures** - Pipeline stops if KFP compilation fails
- **Upload failures** - Pipeline stops if DSP API is unreachable

Check task logs to diagnose issues:

```bash
# List task runs
oc get taskrun -n rhoai-pipelines-demo

# View specific task run logs
oc logs -n rhoai-pipelines-demo <taskrun-pod-name>
```
