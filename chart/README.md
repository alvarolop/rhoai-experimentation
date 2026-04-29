# RHOAI Pipelines Demo Helm Chart

Helm chart for deploying Red Hat OpenShift AI Data Science Pipelines demo with Tekton automation.

## Overview

This chart deploys:

- **Tekton Pipeline** - CI/CD workflow for Kubeflow pipeline deployment
- **Tekton Tasks** - Lint, compile, upload, and run tasks
- **PersistentVolumeClaim** - Workspace storage for pipeline execution
- **S3 Credentials Secret** - For artifact storage
- **Optional Triggers** - Webhook-based pipeline automation

## Prerequisites

- OpenShift cluster with:
  - Red Hat OpenShift AI operator installed
  - DataSciencePipelines server configured
  - OpenShift Pipelines operator installed (v1.15+)
- S3-compatible storage endpoint
- Helm 3.x

## Installation

### Basic Install

```bash
helm install fraud-detection . \
  --set s3.accessKeyId=<your-key> \
  --set s3.secretAccessKey=<your-secret> \
  --set s3.endpoint=<minio-endpoint>
```

### Advanced Install

```bash
helm install fraud-detection . \
  --namespace rhoai-demo \
  --set tekton.image=quay.io/myorg/custom-builder:v1 \
  --set tekton.useClusterTasks=true \
  --set tekton.triggers.enabled=true \
  --set dsp.apiUrl=http://ds-pipeline-dspa.rhoai-demo.svc.cluster.local:8888
```

## Configuration

### Values

| Parameter | Description | Default |
|-----------|-------------|---------|
| `namespace` | Target namespace | `rhoai-pipelines-demo` |
| `createNamespace` | Create namespace if not exists | `false` |
| **DSP Configuration** | | |
| `dsp.apiUrl` | Data Science Pipelines API endpoint | `http://ds-pipeline-dspa...` |
| **Model Registry** | | |
| `modelRegistry.url` | Model Registry service URL | `http://model-registry-service:8080` |
| **S3 Storage** | | |
| `s3.endpoint` | S3 endpoint URL | `minio-service...` |
| `s3.bucket` | Bucket name for artifacts | `pipeline-artifacts` |
| `s3.accessKeyId` | S3 access key ID | `""` (required) |
| `s3.secretAccessKey` | S3 secret access key | `""` (required) |
| **Storage** | | |
| `storage.pvcSize` | PVC size for workspace | `10Gi` |
| `storage.storageClassName` | Storage class name | `""` (default) |
| **Git Repository** | | |
| `git.url` | Git repository URL | `https://github.com/alvarolop/rhoai-experimentation.git` |
| `git.revision` | Branch/tag/SHA to clone | `main` |
| `git.pipelinePath` | Path to pipeline in repo | `pipelines/fraud-detection` |
| **Kubeflow Pipeline** | | |
| `kfpPipeline.name` | Pipeline name | `fraud-detection-pipeline` |
| **Tekton** | | |
| `tekton.enabled` | Enable Tekton resources | `true` |
| `tekton.serviceAccount` | ServiceAccount for pipelines | `pipeline` |
| `tekton.image` | Builder image with KFP SDK | `quay.io/alopezme/rhoai-kfp-builder:latest` |
| `tekton.useClusterTasks` | Use Red Hat ClusterTasks | `true` (recommended) |
| **Tekton Triggers** | | |
| `tekton.triggers.enabled` | Enable webhook triggers | `true` |
| `tekton.triggers.exposeRoute` | Create OpenShift Route | `true` |
| `tekton.triggers.webhookSecret` | Webhook secret for GitHub | `""` (auto-generated) |

### ClusterTasks Configuration

**Recommended (default):**

```yaml
tekton:
  useClusterTasks: true
```

Uses Red Hat maintained ClusterTasks from OpenShift Pipelines operator.

**Custom Tasks:**

```yaml
tekton:
  useClusterTasks: false
```

Deploys custom Task definitions from this chart.

See [Using ClusterTasks](../docs/notes/using-clustertasks.md) for details.

## Usage

### Deploy the Chart

```bash
helm install fraud-detection . \
  --set s3.accessKeyId=$AWS_ACCESS_KEY_ID \
  --set s3.secretAccessKey=$AWS_SECRET_ACCESS_KEY
```

### Trigger Pipeline

**Manual:**

```bash
oc create -f ../tekton/example-run.yaml
```

**Via Webhook:**

Get webhook URL:
```bash
oc get route kfp-webhook-listener -o jsonpath='{.spec.host}'
```

Configure in GitHub → Settings → Webhooks.

### Monitor Pipeline

```bash
# Watch Tekton pipeline
tkn pipelinerun logs -f -n <namespace>

# Check Kubeflow pipeline in RHOAI UI
# Navigate to Data Science Pipelines → Runs
```

## Upgrade

```bash
helm upgrade fraud-detection . \
  --set tekton.image=quay.io/alopezme/rhoai-kfp-builder:v2
```

## Uninstall

```bash
helm uninstall fraud-detection
```

**Note:** PVC and Secrets persist after uninstall. Delete manually if needed:

```bash
oc delete pvc pipeline-workspace -n <namespace>
oc delete secret s3-credentials -n <namespace>
```

## Templates

### Core Resources

- `pipeline-deploy-kfp.yaml` - Main Tekton Pipeline
- `pvc-pipeline-workspace.yaml` - Workspace storage
- `secret-s3-credentials.yaml` - S3 credentials

### Tasks

- `tasks/task-git-clone.yaml` - Clone git repository (only if `useClusterTasks: false`)
- `tasks/task-lint-python.yaml` - Lint Python code with Black, flake8, pylint
- `tasks/task-execute-ds-pipeline.yaml` - Compile, upload, and execute DSP pipeline

### Triggers (if `triggers.enabled: true`)

- `triggers/eventlistener.yaml` - HTTP webhook endpoint
- `triggers/triggerbinding.yaml` - Extract git info from payload
- `triggers/triggertemplate.yaml` - Create PipelineRun
- `triggers/route.yaml` - Expose EventListener

## Troubleshooting

### ClusterTask Not Found

**Error:**
```
error: clustertask.tekton.dev "git-clone" not found
```

**Solution:**

Set `useClusterTasks: false` or install OpenShift Pipelines operator:

```bash
helm upgrade fraud-detection . --set tekton.useClusterTasks=false
```

### S3 Connection Failed

Check S3 credentials:

```bash
oc get secret s3-credentials -o yaml
```

Verify endpoint is reachable:

```bash
oc run -it --rm debug --image=curlimages/curl -- \
  curl -v http://minio-service:9000
```

### Pipeline Permission Errors

Ensure ServiceAccount has permissions:

```bash
oc get rolebinding -n <namespace>
```

Create if needed:

```bash
oc create rolebinding pipeline-admin \
  --clusterrole=admin \
  --serviceaccount=<namespace>:pipeline \
  -n <namespace>
```

## Development

### Template Validation

```bash
helm template fraud-detection . --debug
```

### Dry Run

```bash
helm install fraud-detection . --dry-run --debug
```

### Lint Chart

```bash
helm lint .
```

## Related Documentation

- [Main README](../README.md) - Project overview
- [Using ClusterTasks](../docs/notes/using-clustertasks.md) - ClusterTask vs custom tasks
- [Tekton Triggers Setup](../docs/notes/tekton-triggers-setup.md) - Webhook configuration
- [Architecture](../docs/architecture.md) - System design

## License

GPL-3.0
