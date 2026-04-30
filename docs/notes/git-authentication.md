# Git Authentication for Tekton Pipelines

## Overview

This Helm chart supports optional Git authentication for cloning private repositories. Two authentication methods are available:

1. **SSH Private Key** - Recommended for GitHub, GitLab, and most Git servers
2. **Basic Authentication** - Username/password or personal access token

The authentication is implemented using Tekton's standard authentication mechanism with Secrets that are mounted as workspaces to the `git-clone` task.

## Authentication Methods

### 1. SSH Authentication

**When to use:**
- Private repositories on GitHub, GitLab, Bitbucket
- Preferred method for automated systems
- Better security (no passwords in configuration)

**Requirements:**
- SSH private key (typically `~/.ssh/id_rsa` or `~/.ssh/id_ed25519`)
- SSH public key added to Git service (GitHub → Settings → SSH Keys)
- Optional: `known_hosts` file for enhanced security

**Configuration:**

```yaml
git:
  url: git@github.com:owner/private-repo.git  # Note: SSH URL format
  revision: main
  auth:
    enabled: true
    type: ssh
    sshPrivateKey: |
      -----BEGIN OPENSSH PRIVATE KEY-----
      b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
      ...
      -----END OPENSSH PRIVATE KEY-----
    knownHosts: |
      github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl
```

**Install with SSH auth:**

```bash
# Using file content
SSH_KEY=$(cat ~/.ssh/id_rsa)
KNOWN_HOSTS=$(ssh-keyscan github.com)

helm install fraud-detection chart/ \
  --set git.url="git@github.com:owner/private-repo.git" \
  --set git.auth.enabled=true \
  --set git.auth.type=ssh \
  --set-file git.auth.sshPrivateKey=~/.ssh/id_rsa \
  --set git.auth.knownHosts="$KNOWN_HOSTS"
```

### 2. Basic Authentication

**When to use:**
- Git services that support HTTPS with tokens
- GitHub personal access tokens
- GitLab access tokens
- Basic HTTP auth servers

**Requirements:**
- Username
- Password or personal access token

**Important:** GitHub requires personal access tokens (not passwords) since August 2021.

**Configuration:**

```yaml
git:
  url: https://github.com/owner/private-repo.git  # Note: HTTPS URL
  revision: main
  auth:
    enabled: true
    type: basic
    username: myuser
    password: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # GitHub Personal Access Token
```

**Install with basic auth:**

```bash
helm install fraud-detection chart/ \
  --set git.url="https://github.com/owner/private-repo.git" \
  --set git.auth.enabled=true \
  --set git.auth.type=basic \
  --set git.auth.username=myuser \
  --set git.auth.password=ghp_token
```

## How It Works

### 1. Secret Creation

The Helm chart creates a Kubernetes Secret based on the authentication type:

**SSH Secret (git-auth-ssh):**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: git-auth-ssh
  annotations:
    tekton.dev/git-0: github.com  # Extracted from git.url
type: kubernetes.io/ssh-auth
stringData:
  ssh-privatekey: <private-key-content>
  known_hosts: <known-hosts-content>  # optional
```

**Basic Auth Secret (git-auth-basic):**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: git-auth-basic
  annotations:
    tekton.dev/git-0: https://github.com  # From git.url
type: kubernetes.io/basic-auth
stringData:
  username: <username>
  password: <password-or-token>
```

### 2. Workspace Mounting

The Secret is mounted to the `git-clone` task via a workspace:

```yaml
# In Pipeline spec
workspaces:
  - name: git-ssh-credentials  # or git-basic-credentials
    optional: false

# In git-clone task
tasks:
  - name: git-clone
    workspaces:
      - name: ssh-directory  # or basic-auth
        workspace: git-ssh-credentials
```

### 3. Tekton Integration

Tekton automatically:
1. Reads the Secret with annotation `tekton.dev/git-0`
2. Configures Git credentials before the clone operation
3. For SSH: Creates `~/.ssh/config` with the private key
4. For Basic: Creates `.git-credentials` with username/password

## GitHub Examples

### SSH with GitHub

1. **Generate SSH key** (if you don't have one):
   ```bash
   ssh-keygen -t ed25519 -C "your-email@example.com" -f ~/.ssh/id_ed25519_github
   ```

2. **Add public key to GitHub:**
   - Copy: `cat ~/.ssh/id_ed25519_github.pub`
   - GitHub → Settings → SSH and GPG keys → New SSH key

3. **Get known_hosts for GitHub:**
   ```bash
   ssh-keyscan github.com > /tmp/github_known_hosts
   ```

4. **Deploy with Helm:**
   ```bash
   helm install fraud-detection chart/ \
     --set git.url="git@github.com:owner/repo.git" \
     --set git.auth.enabled=true \
     --set git.auth.type=ssh \
     --set-file git.auth.sshPrivateKey=~/.ssh/id_ed25519_github \
     --set-file git.auth.knownHosts=/tmp/github_known_hosts \
     --set s3.accessKeyId=<key> \
     --set s3.secretAccessKey=<secret>
   ```

### Personal Access Token with GitHub

1. **Create GitHub PAT:**
   - GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Generate new token with `repo` scope
   - Copy the token (e.g., `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

2. **Deploy with Helm:**
   ```bash
   helm install fraud-detection chart/ \
     --set git.url="https://github.com/owner/private-repo.git" \
     --set git.auth.enabled=true \
     --set git.auth.type=basic \
     --set git.auth.username=your-github-username \
     --set git.auth.password=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
     --set s3.accessKeyId=<key> \
     --set s3.secretAccessKey=<secret>
   ```

## GitLab Examples

### SSH with GitLab

```bash
helm install fraud-detection chart/ \
  --set git.url="git@gitlab.com:owner/repo.git" \
  --set git.auth.enabled=true \
  --set git.auth.type=ssh \
  --set-file git.auth.sshPrivateKey=~/.ssh/id_rsa \
  --set git.auth.knownHosts="$(ssh-keyscan gitlab.com)"
```

### Access Token with GitLab

```bash
# GitLab access token as username, with 'gitlab-ci-token' or any username
helm install fraud-detection chart/ \
  --set git.url="https://gitlab.com/owner/repo.git" \
  --set git.auth.enabled=true \
  --set git.auth.type=basic \
  --set git.auth.username=gitlab-ci-token \
  --set git.auth.password=<gitlab-access-token>
```

## Security Best Practices

### 1. Don't Commit Secrets

**Never** commit private keys or tokens to Git. Use:
- `--set-file` for SSH keys
- `--set` from environment variables
- External secret management (Vault, Sealed Secrets)

### 2. Use known_hosts

Always provide `known_hosts` for SSH to prevent MITM attacks:

```bash
ssh-keyscan github.com >> ~/.ssh/known_hosts
```

### 3. Limit Token Scope

For GitHub PATs:
- Use fine-grained tokens when possible
- Only grant `repo` scope (read-only if possible)
- Set expiration dates

### 4. External Secret Management

For production environments, use external secret management:

**Example with External Secrets Operator:**

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: git-auth-ssh
spec:
  secretStoreRef:
    name: vault-backend
  target:
    name: git-auth-ssh
    template:
      type: kubernetes.io/ssh-auth
      metadata:
        annotations:
          tekton.dev/git-0: github.com
  data:
    - secretKey: ssh-privatekey
      remoteRef:
        key: git-ssh-keys
        property: private-key
```

## Troubleshooting

### SSH: Permission Denied

**Error:**
```
Permission denied (publickey).
fatal: Could not read from remote repository.
```

**Solutions:**

1. Verify public key is added to Git service
2. Check SSH key format (should be OpenSSH format)
3. Verify `git.url` uses SSH format: `git@github.com:...`
4. Check Secret was created: `oc get secret git-auth-ssh -o yaml`

### SSH: Host Key Verification Failed

**Error:**
```
Host key verification failed.
fatal: Could not read from remote repository.
```

**Solution:**

Add `known_hosts`:
```bash
--set git.auth.knownHosts="$(ssh-keyscan github.com)"
```

### Basic Auth: Authentication Failed

**Error:**
```
remote: Support for password authentication was removed on August 13, 2021.
fatal: Authentication failed
```

**Solution:**

Use personal access token instead of password:
```bash
--set git.auth.password=ghp_token  # Not your GitHub password
```

### Secret Not Mounted

**Error:**
```
error: workspace "ssh-directory" is not defined
```

**Solution:**

Ensure PipelineRun includes the workspace binding:
```yaml
workspaces:
  - name: git-ssh-credentials
    secret:
      secretName: git-auth-ssh
```

### Wrong URL Format

**Error:**
```
fatal: repository 'https://github.com/owner/repo/' not found
```

**Solutions:**

- For SSH auth: Use `git@github.com:owner/repo.git`
- For basic auth: Use `https://github.com/owner/repo.git`
- Verify repository exists and you have access

## Testing Authentication

### Test SSH Access

```bash
# From a pod with the secret mounted
oc run -it --rm test-ssh \
  --image=registry.access.redhat.com/ubi9/ubi \
  --overrides='
{
  "spec": {
    "containers": [{
      "name": "test-ssh",
      "image": "registry.access.redhat.com/ubi9/ubi",
      "command": ["sh", "-c", "dnf install -y git openssh-clients && bash"],
      "volumeMounts": [{
        "name": "ssh",
        "mountPath": "/root/.ssh"
      }]
    }],
    "volumes": [{
      "name": "ssh",
      "secret": {"secretName": "git-auth-ssh"}
    }]
  }
}' -- bash

# Inside the pod:
chmod 600 /root/.ssh/ssh-privatekey
ssh -i /root/.ssh/ssh-privatekey -T git@github.com
```

### Test Basic Auth

```bash
# Using curl
oc get secret git-auth-basic -o jsonpath='{.data.username}' | base64 -d
oc get secret git-auth-basic -o jsonpath='{.data.password}' | base64 -d

# Test with git
git ls-remote https://username:token@github.com/owner/repo.git
```

## References

- [OpenShift Pipelines - Authenticating with Git](https://docs.redhat.com/en/documentation/red_hat_openshift_pipelines/1.15/html/securing_openshift_pipelines/authenticating-pipelines-repos-using-secrets)
- [Tekton Authentication Documentation](https://tekton.dev/docs/pipelines/auth/)
- [GitHub SSH Key Setup](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
- [GitHub Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)

## Related Files

- `chart/values.yaml` - Git authentication configuration
- `chart/templates/secret-git-auth-ssh.yaml` - SSH Secret template
- `chart/templates/secret-git-auth-basic.yaml` - Basic auth Secret template
- `chart/templates/pipeline-deploy-kfp.yaml` - Pipeline with authentication workspace
- `tekton/example-run.yaml` - Example PipelineRun with auth workspace bindings
