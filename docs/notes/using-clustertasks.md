# Using Red Hat OpenShift Pipelines ClusterTasks

## Overview

Red Hat OpenShift Pipelines provides **ClusterTasks** - pre-built, maintained, and certified task definitions available cluster-wide. These tasks are installed automatically with the OpenShift Pipelines operator.

## Benefits of ClusterTasks

✅ **Maintained by Red Hat** - Updates and security patches handled automatically  
✅ **Tested and certified** - Production-ready and verified  
✅ **No custom maintenance** - No need to maintain your own task definitions  
✅ **Consistent across clusters** - Same behavior everywhere  
✅ **Latest features** - Always up-to-date with operator version

## Available ClusterTasks

Common ClusterTasks included with OpenShift Pipelines:

- **git-clone** - Clone a git repository
- **buildah** - Build container images using Buildah
- **s2i** - Source-to-Image builds
- **maven** - Maven builds
- **helm-upgrade** - Deploy Helm charts
- And many more...

List all available ClusterTasks:

```bash
oc get clustertask
```

View a specific ClusterTask:

```bash
oc get clustertask git-clone -o yaml
```

## Using ClusterTasks in This Demo

This demo uses the **git-clone ClusterTask** by default.

### Configuration

In `chart/values.yaml`:

```yaml
tekton:
  useClusterTasks: true  # Use Red Hat ClusterTasks (default)
```

### Switching Between ClusterTask and Custom Task

**Option 1: Use ClusterTask (Recommended)**

```yaml
tekton:
  useClusterTasks: true
```

This references the Red Hat maintained ClusterTask. Requires OpenShift Pipelines operator installed.

**Option 2: Use Custom Task**

```yaml
tekton:
  useClusterTasks: false
```

This deploys and uses our custom Task definition from `chart/templates/tasks/task-git-clone.yaml`.

Useful when:
- Testing modifications to the task
- Running in environments without the ClusterTask
- Need specific parameters not available in ClusterTask

### Override During Install

```bash
# Use ClusterTask
helm install fraud-detection chart/ \
  --set tekton.useClusterTasks=true

# Use custom Task
helm install fraud-detection chart/ \
  --set tekton.useClusterTasks=false
```

## Git-Clone ClusterTask Details

The Red Hat `git-clone` ClusterTask provides:

- **Repository cloning** with authentication support
- **Sparse checkout** for monorepos
- **Submodule support**
- **LFS support** (Git Large File Storage)
- **SSL verification** options
- **Proxy support**

### Parameters

Key parameters (check actual ClusterTask for full list):

| Parameter | Description | Default |
|-----------|-------------|---------|
| `url` | Git repository URL | (required) |
| `revision` | Branch, tag, or SHA | `main` |
| `subdirectory` | Clone into subdirectory | `""` |
| `deleteExisting` | Clean workspace before clone | `true` |
| `depth` | Git clone depth (0=full history) | `1` |

### Workspaces

| Workspace | Description |
|-----------|-------------|
| `output` | Directory to clone into |
| `ssh-directory` | SSH credentials (optional) |
| `basic-auth` | HTTP basic auth (optional) |

## Troubleshooting

### ClusterTask Not Found

**Error:**
```
error: clustertask.tekton.dev "git-clone" not found
```

**Solution:**

1. Check OpenShift Pipelines operator is installed:
   ```bash
   oc get subscription -n openshift-operators openshift-pipelines-operator
   ```

2. Verify ClusterTasks are available:
   ```bash
   oc get clustertask
   ```

3. If not available, either:
   - Install OpenShift Pipelines operator
   - Or set `tekton.useClusterTasks: false` to use custom Task

### Version Compatibility

Different OpenShift Pipelines versions include different ClusterTask versions.

Check your operator version:

```bash
oc get csv -n openshift-operators | grep pipelines
```

For OpenShift Pipelines 1.15+, the git-clone ClusterTask uses RHEL9-based images.

### Using Custom Task as Fallback

The Helm chart includes a custom Task definition in `chart/templates/tasks/task-git-clone.yaml`.

This is deployed when `tekton.useClusterTasks: false` and can serve as:
- **Fallback** if ClusterTask is unavailable
- **Template** for customization
- **Reference** for understanding task structure

## Best Practices

1. **Prefer ClusterTasks** - Use them whenever available for easier maintenance
2. **Version awareness** - Check ClusterTask version matches your needs
3. **Custom when needed** - Only create custom tasks for specific requirements
4. **Document overrides** - If modifying default behavior, document why
5. **Test both modes** - Verify your pipeline works with both ClusterTask and custom Task

## Additional Resources

- [OpenShift Pipelines Documentation](https://docs.openshift.com/pipelines/latest/about/understanding-openshift-pipelines.html)
- [Tekton Hub](https://hub.tekton.dev/) - Browse community tasks
- [Red Hat OpenShift Pipelines Catalog](https://github.com/openshift/pipelines-catalog)

## Related Files

- `chart/values.yaml` - Configuration for ClusterTask usage
- `chart/templates/pipeline-deploy-kfp.yaml` - Pipeline definition using git-clone
- `chart/templates/tasks/task-git-clone.yaml` - Custom Task fallback definition
