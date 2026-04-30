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
| **Git Authentication** | | |
| `git.auth.enabled` | Enable Git authentication | `false` |
| `git.auth.type` | Auth type: `ssh` or `basic` | `ssh` |
| `git.auth.sshPrivateKey` | SSH private key content | `""` |
| `git.auth.knownHosts` | SSH known_hosts content | `""` (optional) |
| `git.auth.username` | Git username (basic auth) | `""` |
| `git.auth.password` | Password or token (basic auth) | `""` |
| **Kubeflow Pipeline** | | |
| `kfpPipeline.name` | Pipeline name | `fraud-detection-pipeline` |
| **Tekton** | | |
| `tekton.enabled` | Enable Tekton resources | `true` |
| `tekton.serviceAccount` | ServiceAccount for pipelines | `pipeline` |
| `tekton.image` | Builder image with KFP SDK | `quay.io/alopezme/rhoai-kfp-builder:latest` |
| **Tekton Triggers** | | |
| `tekton.triggers.enabled` | Enable webhook triggers | `true` |
| `tekton.triggers.exposeRoute` | Create OpenShift Route | `true` |
| `tekton.triggers.webhookSecret` | Webhook secret for GitHub | `""` (auto-generated) |

### Red Hat Tasks Integration

This chart uses **Red Hat provided tasks** from the `openshift-pipelines` namespace via cluster resolver. 

The `git-clone` task is referenced automatically:

```yaml
taskRef:
  resolver: cluster
  params:
    - name: kind
      value: task
    - name: name
      value: git-clone
    - name: namespace
      value: openshift-pipelines
```

**Requirements:**
- OpenShift Pipelines operator 1.15 or later installed
- Tasks are maintained by Red Hat and updated automatically

See [Using Red Hat Tasks](../docs/notes/using-red-hat-tasks.md) for details.

### Git Authentication

Optionally configure authentication for private Git repositories:

**SSH Authentication (recommended):**

```bash
helm install fraud-detection . \
  --set git.url="git@github.com:owner/private-repo.git" \
  --set git.auth.enabled=true \
  --set git.auth.type=ssh \
  --set-file git.auth.sshPrivateKey=~/.ssh/id_rsa \
  --set git.auth.knownHosts="$(ssh-keyscan github.com)" \
  --set s3.accessKeyId=<key> \
  --set s3.secretAccessKey=<secret>
```

**Basic Authentication (token):**

```bash
helm install fraud-detection . \
  --set git.url="https://github.com/owner/private-repo.git" \
  --set git.auth.enabled=true \
  --set git.auth.type=basic \
  --set git.auth.username=myuser \
  --set git.auth.password=ghp_token \
  --set s3.accessKeyId=<key> \
  --set s3.secretAccessKey=<secret>
```

See [Git Authentication Guide](../docs/notes/git-authentication.md) for complete documentation.

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

- `tasks/task-lint-python.yaml` - Lint Python code with Black, flake8, pylint
- `tasks/task-execute-ds-pipeline.yaml` - Compile, upload, and execute DSP pipeline

**Note:** The `git-clone` task is provided by Red Hat in the `openshift-pipelines` namespace and is not part of this chart.

### Triggers (if `triggers.enabled: true`)

- `triggers/eventlistener.yaml` - HTTP webhook endpoint
- `triggers/triggerbinding.yaml` - Extract git info from payload
- `triggers/triggertemplate.yaml` - Create PipelineRun
- `triggers/route.yaml` - Expose EventListener

## Troubleshooting

### Task Not Found

**Error:**
```
error: tasks.tekton.dev "git-clone" not found in namespace openshift-pipelines
```

**Solution:**

Install or verify OpenShift Pipelines operator (v1.15+) is installed:

```bash
oc get subscription -n openshift-operators openshift-pipelines-operator
oc get task -n openshift-pipelines | grep git-clone
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
- [Using Red Hat Tasks](../docs/notes/using-red-hat-tasks.md) - Red Hat provided tasks via cluster resolver
- [Git Authentication](../docs/notes/git-authentication.md) - SSH and basic auth for private repositories
- [Tekton Triggers Setup](../docs/notes/tekton-triggers-setup.md) - Webhook configuration
- [Architecture](../docs/architecture.md) - System design

## License

GPL-3.0
