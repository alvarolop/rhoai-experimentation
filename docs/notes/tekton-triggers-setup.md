# Tekton Triggers Setup

This document explains how to configure GitHub webhooks to automatically trigger pipeline runs.

## Architecture

```
GitHub Push
    │
    ▼
GitHub Webhook
    │
    ▼
OpenShift Route (TLS)
    │
    ▼
EventListener Service
    │
    ▼
TriggerBinding (extract webhook data)
    │
    ▼
TriggerTemplate (create PipelineRun)
    │
    ▼
Tekton Pipeline Execution
```

## Components

### EventListener
- Receives webhook payloads
- Validates GitHub webhook secret
- Triggers TriggerTemplate

### TriggerBinding
Extracts data from webhook payload:
- `git-url`: Repository clone URL
- `git-revision`: Commit SHA
- `git-repo-name`: Repository name

### TriggerTemplate
Creates PipelineRun with:
- Git URL and revision from webhook
- Pipeline path from values.yaml
- DSP API URL

### Route
Exposes EventListener externally with TLS termination.

## Setup Instructions

### 1. Get the Webhook URL

After Helm install:

```bash
oc get route kfp-webhook-listener -n rhoai-pipelines-demo -o jsonpath='{.spec.host}'
```

The webhook URL will be: `https://<route-host>`

### 2. Configure GitHub Webhook

In your GitHub repository:

1. Go to **Settings → Webhooks → Add webhook**
2. **Payload URL**: `https://<route-host>` (from step 1)
3. **Content type**: `application/json`
4. **Secret**: The webhook secret (set in values.yaml or Helm install)
5. **Events**: Select "Just the push event"
6. **Active**: ✓ Enabled

### 3. Set Webhook Secret

During Helm install:

```bash
helm install fraud-detection chart/ \
  --set tekton.triggers.webhookSecret=<your-secret> \
  --set s3.accessKeyId=<key> \
  --set s3.secretAccessKey=<secret>
```

Or update after install:

```bash
oc create secret generic github-webhook-secret \
  --from-literal=secret=<your-secret> \
  -n rhoai-pipelines-demo \
  --dry-run=client -o yaml | oc apply -f -
```

### 4. Test the Webhook

Push a commit to your repository:

```bash
git commit --allow-empty -m "Test webhook trigger"
git push
```

Monitor pipeline runs:

```bash
oc get pipelinerun -n rhoai-pipelines-demo -w
```

## Webhook Payload

GitHub sends:

```json
{
  "repository": {
    "clone_url": "https://github.com/user/repo.git",
    "name": "repo"
  },
  "after": "abc123..." // commit SHA
}
```

TriggerBinding extracts these fields and passes them to TriggerTemplate.

## Filtering Events

Currently configured for:
- Push events only
- All branches

To filter by branch, add to EventListener:

```yaml
interceptors:
  - ref:
      name: cel
    params:
      - name: filter
        value: "body.ref == 'refs/heads/main'"
```

## Security

- Webhook secret validates requests from GitHub
- TLS encryption via OpenShift Route
- ServiceAccount with minimal RBAC permissions
- EventListener validates GitHub signature

## Troubleshooting

### Webhook Not Triggering

Check EventListener logs:
```bash
oc logs -n rhoai-pipelines-demo -l eventlistener=kfp-webhook
```

### Invalid Signature

Verify webhook secret matches:
```bash
oc get secret github-webhook-secret -n rhoai-pipelines-demo -o jsonpath='{.data.secret}' | base64 -d
```

### Route Not Accessible

Check route status:
```bash
oc get route kfp-webhook-listener -n rhoai-pipelines-demo
```

## Manual Testing

Trigger without webhook:

```bash
cat <<EOF | oc create -f -
apiVersion: triggers.tekton.dev/v1beta1
kind: EventListener
metadata:
  name: test-trigger
spec:
  serviceAccountName: tekton-triggers-sa
  triggers:
    - bindings:
        - ref: kfp-webhook-binding
      template:
        ref: kfp-pipeline-template
EOF
```

Or use curl to simulate webhook:

```bash
curl -X POST https://<route-host> \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=<signature>" \
  -d @webhook-payload.json
```
