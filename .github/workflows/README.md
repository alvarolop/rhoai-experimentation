# GitHub Workflows

Automated CI/CD workflows for the RHOAI Pipelines Demo.

## Workflows

### Build and Push Container Image

**File**: `build-push-image.yaml`

Automatically builds and pushes the custom builder image to Quay.io when changes are detected.

#### Triggers

1. **Push to main** - Builds and pushes with tags:
   - `latest`
   - `<commit-sha>` (short)

2. **Pull Request** - Builds only (dry-run, no push)
   - Validates Containerfile
   - Posts build details as PR comment

3. **Manual dispatch** - Via GitHub Actions UI
   - Allows custom tag input

#### Monitored paths

- `container-image/**` - Containerfile changes
- `pipelines/**/requirements.txt` - Dependency changes
- `.github/workflows/build-push-image.yaml` - Workflow changes

#### Image tags

The workflow generates multiple tags:

```
quay.io/alopezme/rhoai-kfp-builder:latest          # Latest from main
quay.io/alopezme/rhoai-kfp-builder:a1b2c3d         # Commit SHA
quay.io/alopezme/rhoai-kfp-builder:v1.0.0          # Semantic version (if tag pushed)
quay.io/alopezme/rhoai-kfp-builder:1.0             # Major.minor (if tag pushed)
```

#### Configuration

**Required Secrets** (in GitHub repository settings):

1. **`QUAY_USERNAME`** - Quay.io username
2. **`QUAY_PASSWORD`** - Quay.io password or robot account token

**Set secrets**:
```
Settings → Secrets and variables → Actions → New repository secret
```

**Recommended**: Use a [Quay.io Robot Account](https://docs.quay.io/glossary/robot-accounts.html) instead of personal credentials:

1. Create robot account in Quay.io
2. Grant write permissions to `alopezme/rhoai-kfp-builder` repository
3. Use robot account credentials in secrets

#### Multi-architecture builds

Builds for both:
- `linux/amd64` (x86_64)
- `linux/arm64` (aarch64)

Useful for:
- Development on Apple Silicon Macs
- ARM-based cloud instances
- Raspberry Pi (if testing locally)

#### Build cache

Uses GitHub Actions cache to speed up builds:
- Cache images from previous runs
- Reuse unchanged layers
- Faster builds for small changes

#### Usage

**Automatic (on push to main)**:

```bash
git add container-image/Containerfile
git commit -m "Update KFP SDK to 2.14"
git push origin main
# Workflow triggers automatically
```

**Manual trigger**:

1. Go to Actions → Build and Push Container Image
2. Click "Run workflow"
3. (Optional) Enter custom tag
4. Click "Run workflow" button

**Check build status**:

```bash
# View workflow runs
gh run list --workflow=build-push-image.yaml

# View specific run logs
gh run view <run-id> --log
```

#### Semantic versioning

To trigger semantic version tags:

```bash
# Tag a release
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# Workflow creates tags:
# - quay.io/alopezme/rhoai-kfp-builder:v1.0.0
# - quay.io/alopezme/rhoai-kfp-builder:1.0
# - quay.io/alopezme/rhoai-kfp-builder:latest
```

#### Troubleshooting

**Authentication failed**:
```
Error: buildx failed with: error: failed to solve: failed to do request: Head "https://quay.io/v2/...": unauthorized
```

Solution: Check `QUAY_USERNAME` and `QUAY_PASSWORD` secrets are set correctly.

**Build cache issues**:

Clear cache in repository settings:
```
Settings → Actions → Caches → Delete all caches
```

**Workflow not triggering**:

Verify paths in workflow match changed files:
```bash
git log --oneline --name-only
```

## Future Workflows

Potential additions:

- **Lint and Test Pipeline Code** - Validate Python syntax before merge
- **Scan for Vulnerabilities** - Trivy/Snyk security scanning
- **Deploy to Test Cluster** - Automated e2e testing
- **Update Helm Chart** - Automatically bump image tag in values.yaml

## Related Documentation

- [Container Image README](../container-image/README.md)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [Quay.io Documentation](https://docs.quay.io/)
