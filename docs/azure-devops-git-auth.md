# Azure DevOps Server Git Authentication for Tekton

This guide configures the `git-clone` task to authenticate with on-premise Azure DevOps Server for pipeline execution.

## Overview

The Red Hat Tekton `git-clone` task supports multiple authentication methods. Azure DevOps Server requires specific configuration depending on your authentication method.

## Authentication Methods

### Method 1: SSH Authentication (Recommended)

SSH authentication is more secure and doesn't require credential rotation.

#### 1. Generate SSH Key Pair

```bash
# Generate SSH key (no passphrase for automation)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/azure-devops -N ""

# View public key to add to Azure DevOps
cat ~/.ssh/azure-devops.pub
```

#### 2. Add SSH Key to Azure DevOps

1. Navigate to Azure DevOps → User Settings → SSH Public Keys
2. Click "Add" and paste the public key from step 1
3. Save

#### 3. Create Kubernetes Secret

```bash
# Create secret with SSH private key
oc create secret generic azure-devops-ssh \
  --from-file=ssh-privatekey=$HOME/.ssh/azure-devops \
  --type=kubernetes.io/ssh-auth \
  -n rhoai-playground

# Annotate with Azure DevOps Server hostname
oc annotate secret azure-devops-ssh \
  git-server='ssh.dev.azure.com' \
  -n rhoai-playground
```

**For on-premise Azure DevOps Server**, use your server's hostname:

```bash
oc annotate secret azure-devops-ssh \
  git-server='azuredevops.yourcompany.com' \
  -n rhoai-playground
```

#### 4. Configure Git Clone Task

Update your Tekton PipelineRun to reference the SSH secret:

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: fraud-detection-run
spec:
  pipelineRef:
    name: fraud-detection
  workspaces:
    - name: output
      volumeClaimTemplate:
        spec:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 1Gi
    - name: ssh-credentials  # Add SSH workspace
      secret:
        secretName: azure-devops-ssh
  params:
    - name: GIT_URL
      value: "ssh://git@azuredevops.yourcompany.com:22/YourOrg/YourProject/_git/repo"
```

#### 5. Update Pipeline Definition

Ensure your pipeline declares the SSH credentials workspace:

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: fraud-detection
spec:
  workspaces:
    - name: output
    - name: ssh-credentials  # Add this
      optional: false
  tasks:
    - name: git-clone
      taskRef:
        resolver: cluster
        params:
          - name: kind
            value: task
          - name: name
            value: git-clone
          - name: namespace
            value: openshift-pipelines
      workspaces:
        - name: output
          workspace: output
        - name: ssh-directory  # Map to SSH credentials
          workspace: ssh-credentials
      params:
        - name: url
          value: "$(params.GIT_URL)"
```

---

### Method 2: Basic Authentication (Username/Password or PAT)

For environments where SSH is not available, use HTTP(S) with credentials.

#### 1. Generate Personal Access Token (PAT)

Azure DevOps Server → User Settings → Personal Access Tokens → New Token

Permissions needed:
- Code (Read)

**Important**: Copy the token immediately - it won't be shown again.

#### 2. URL Encoding for Special Characters

If your username or password contains special characters, they must be URL-encoded in the `.git-credentials` file.

**Common special characters in usernames:**

| Character | URL Encoded | Example Use Case |
|-----------|-------------|------------------|
| `@` | `%40` | Email as username: `user@company.com` → `user%40company.com` |
| `\` | `%5C` | Domain username: `DOMAIN\user` → `DOMAIN%5Cuser` |
| `:` | `%3A` | Rare but possible in usernames |
| `/` | `%2F` | Forward slash |
| `?` | `%3F` | Question mark |
| `#` | `%23` | Hash/pound |
| `%` | `%25` | Percent itself |

**Common special characters in passwords/tokens:**

Same encoding applies to PAT tokens if they contain special characters (rare but possible).

**Examples:**

```bash
# Username with @ symbol (email)
# user@company.com with token abc123
https://user%40company.com:abc123@azuredevops.yourcompany.com

# Domain username with backslash
# DOMAIN\username with token abc123
https://DOMAIN%5Cusername:abc123@azuredevops.yourcompany.com

# Username with both @ and \
# DOMAIN\user@company.com with token abc123
https://DOMAIN%5Cuser%40company.com:abc123@azuredevops.yourcompany.com

# Token with special characters (if needed)
# username with token abc:123/xyz
https://username:abc%3A123%2Fxyz@azuredevops.yourcompany.com
```

**Quick URL encoding script:**

```bash
# Encode username
echo -n "DOMAIN\username" | jq -sRr @uri
# Output: DOMAIN%5Cusername

# Encode email
echo -n "user@company.com" | jq -sRr @uri
# Output: user%40company.com
```

#### 3. Create Kubernetes Secret with Basic Auth

The secret must contain both `.git-credentials` and `.gitconfig` files.

**Option A: Using kubectl create secret** (RECOMMENDED)

```bash
# Create .git-credentials file
# NOTE: If username contains special characters (like @ or \), use URL encoding (see section 2)
# Example: DOMAIN\user becomes DOMAIN%5Cuser
cat > /tmp/.git-credentials <<EOF
https://username:TOKEN@azuredevops.yourcompany.com
EOF

# Create .gitconfig file
cat > /tmp/.gitconfig <<EOF
[credential]
    helper = store
[credential "https://azuredevops.yourcompany.com"]
    useHttpPath = true
EOF

# Create secret
oc create secret generic azure-devops-basic \
  --from-file=.git-credentials=/tmp/.git-credentials \
  --from-file=.gitconfig=/tmp/.gitconfig \
  -n rhoai-playground

# Clean up
rm /tmp/.git-credentials /tmp/.gitconfig
```

**Option B: Using YAML manifest** (if kubectl create doesn't work)

```bash
# Base64 encode credentials
# NOTE: If username contains special characters (like @ or \), use URL encoding (see section 2)
# Example: DOMAIN\user becomes DOMAIN%5Cuser
GIT_CREDS=$(cat <<EOF | base64 -w 0
https://username:TOKEN@azuredevops.yourcompany.com
EOF
)

GIT_CONFIG=$(cat <<EOF | base64 -w 0
[credential]
    helper = store
[credential "https://azuredevops.yourcompany.com"]
    useHttpPath = true
EOF
)

# Create secret manifest
cat > azure-devops-basic-secret.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: azure-devops-basic
  namespace: rhoai-playground
type: Opaque
data:
  .git-credentials: ${GIT_CREDS}
  .gitconfig: ${GIT_CONFIG}
EOF

# Apply
oc apply -f azure-devops-basic-secret.yaml
rm azure-devops-basic-secret.yaml
```

#### 4. Configure Git Clone Task for Basic Auth

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: fraud-detection-run
spec:
  pipelineRef:
    name: fraud-detection
  workspaces:
    - name: output
      volumeClaimTemplate:
        spec:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 1Gi
    - name: basic-auth  # Add basic auth workspace
      secret:
        secretName: azure-devops-basic
  params:
    - name: GIT_URL
      value: "https://azuredevops.yourcompany.com/YourOrg/YourProject/_git/repo"
```

#### 5. Update Pipeline for Basic Auth

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: fraud-detection
spec:
  workspaces:
    - name: output
    - name: basic-auth  # Add this
      optional: false
  tasks:
    - name: git-clone
      taskRef:
        resolver: cluster
        params:
          - name: kind
            value: task
          - name: name
            value: git-clone
          - name: namespace
            value: openshift-pipelines
      workspaces:
        - name: output
          workspace: output
        - name: basic-auth  # Map to basic auth credentials
          workspace: basic-auth
      params:
        - name: url
          value: "$(params.GIT_URL)"
```

---

## Troubleshooting

### Issue: .git-credentials file is empty

**Root Cause**: Secret not properly mounted or wrong key name.

**Solution 1**: Verify secret contents

```bash
# Check secret has correct keys
oc get secret azure-devops-basic -o yaml

# Should show:
#   data:
#     .git-credentials: <base64>
#     .gitconfig: <base64>

# Decode to verify content
oc get secret azure-devops-basic -o jsonpath='{.data.\.git-credentials}' | base64 -d

# Should output:
# https://username:TOKEN@azuredevops.yourcompany.com
```

**Solution 2**: Verify workspace mapping

The git-clone task expects the secret to be mounted at `/workspace/basic-auth`. Check the task logs:

```bash
oc logs <git-clone-pod> | grep -A 5 "basic-auth"
```

**Solution 3**: Re-create secret using exact key names

The keys MUST be exactly `.git-credentials` and `.gitconfig` (including the dot prefix):

```bash
# Delete old secret
oc delete secret azure-devops-basic

# Create with exact key names
# NOTE: If username contains special characters (like @ or \), use URL encoding
# Example: DOMAIN\user becomes DOMAIN%5Cuser (see Method 2, section 2)
oc create secret generic azure-devops-basic \
  --from-literal='.git-credentials'='https://username:TOKEN@azuredevops.yourcompany.com' \
  --from-literal='.gitconfig'='[credential]
    helper = store
[credential "https://azuredevops.yourcompany.com"]
    useHttpPath = true' \
  -n rhoai-playground
```

### Issue: Authentication fails with 401

**Possible Causes**:
1. PAT expired
2. Wrong URL format
3. Insufficient PAT permissions

**Solutions**:

```bash
# Test credentials manually
git clone https://username:TOKEN@azuredevops.yourcompany.com/YourOrg/YourProject/_git/repo

# Verify PAT permissions in Azure DevOps:
# - Code (Read)
# - Check expiration date

# Try with different URL format (Azure DevOps supports multiple formats):
# Format 1: https://azuredevops.yourcompany.com/YourOrg/YourProject/_git/repo
# Format 2: https://azuredevops.yourcompany.com/YourOrg/_git/repo
# Format 3: https://YourOrg@dev.azure.com/YourOrg/YourProject/_git/repo (cloud only)
```

### Issue: SSL certificate verification failed

For on-premise servers with self-signed certificates:

```bash
# Option 1: Add CA certificate to secret (RECOMMENDED)
oc create secret generic azure-devops-basic \
  --from-file=.git-credentials=/tmp/.git-credentials \
  --from-file=.gitconfig=/tmp/.gitconfig \
  --from-file=ca-bundle.crt=/path/to/ca-cert.pem \
  -n rhoai-playground

# Option 2: Disable SSL verification (NOT RECOMMENDED for production)
cat > /tmp/.gitconfig <<EOF
[credential]
    helper = store
[http]
    sslVerify = false
EOF
```

### Debug Mode

Enable verbose logging in git-clone task:

```yaml
tasks:
  - name: git-clone
    params:
      - name: verbose
        value: "true"  # Enable debug output
      - name: url
        value: "$(params.GIT_URL)"
```

---

## Testing Authentication

### Test SSH Authentication

```bash
# From your local machine or a debug pod
ssh -T git@azuredevops.yourcompany.com -i ~/.ssh/azure-devops

# Expected output:
# remote: Azure DevOps Server
# shell request failed on channel 0
```

### Test Basic Authentication

```bash
# Test with curl
curl -u username:TOKEN https://azuredevops.yourcompany.com/YourOrg/YourProject/_git/repo/info/refs?service=git-upload-pack

# Should return git protocol response (not 401)
```

---

## Helm Chart Integration

To make authentication configurable via Helm values:

### values.yaml

```yaml
git:
  url: "https://azuredevops.yourcompany.com/YourOrg/YourProject/_git/repo"
  authType: "basic"  # or "ssh"
  
  # For basic auth
  basicAuth:
    secretName: "azure-devops-basic"
  
  # For SSH
  sshAuth:
    secretName: "azure-devops-ssh"
```

### template update

```yaml
{{- if eq .Values.git.authType "basic" }}
  workspaces:
    - name: basic-auth
      secret:
        secretName: {{ .Values.git.basicAuth.secretName }}
{{- else if eq .Values.git.authType "ssh" }}
  workspaces:
    - name: ssh-credentials
      secret:
        secretName: {{ .Values.git.sshAuth.secretName }}
{{- end }}
```

---

## References

- [Tekton git-clone task documentation](https://hub.tekton.dev/tekton/task/git-clone)
- [Azure DevOps SSH documentation](https://docs.microsoft.com/en-us/azure/devops/repos/git/use-ssh-keys-to-authenticate)
- [Azure DevOps PAT documentation](https://docs.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate)
- [Git credential storage](https://git-scm.com/docs/git-credential-store)
