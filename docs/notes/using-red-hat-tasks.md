# Using Red Hat OpenShift Pipelines Tasks

## Overview

Red Hat OpenShift Pipelines (version 1.15+) provides **pre-built, maintained, and certified task definitions** in the `openshift-pipelines` namespace. These tasks are installed automatically with the OpenShift Pipelines operator and are referenced using the **cluster resolver**.

## Important: ClusterTasks Deprecated

Starting with OpenShift Pipelines 1.15, **ClusterTasks are deprecated**. Instead, Red Hat provides regular Tasks in the `openshift-pipelines` namespace that can be referenced cluster-wide using the cluster resolver.

### Migration from ClusterTasks

**Before (ClusterTask - deprecated):**
```yaml
taskRef:
  kind: ClusterTask
  name: git-clone
```

**After (Cluster Resolver - current):**
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

## Benefits of Red Hat Provided Tasks

✅ **Maintained by Red Hat** - Updates and security patches handled automatically  
✅ **Tested and certified** - Production-ready and verified  
✅ **No custom maintenance** - No need to maintain your own task definitions  
✅ **Consistent across clusters** - Same behavior everywhere  
✅ **Latest features** - Always up-to-date with operator version  
✅ **Namespace-scoped** - Better RBAC and isolation than ClusterTasks

## Available Red Hat Tasks

Common tasks included with OpenShift Pipelines 1.15+:

- **git-clone** - Clone a git repository
- **buildah** - Build container images using Buildah
- **s2i** - Source-to-Image builds
- **maven** - Maven builds
- **helm-upgrade** - Deploy Helm charts
- And many more...

List all available tasks in openshift-pipelines namespace:

```bash
oc get task -n openshift-pipelines
```

View a specific task:

```bash
oc get task git-clone -n openshift-pipelines -o yaml
```

## Using Red Hat Tasks in This Demo

This demo uses the **git-clone task** from the `openshift-pipelines` namespace via cluster resolver.

### Pipeline Configuration

In `chart/templates/pipeline-deploy-kfp.yaml`:

```yaml
tasks:
  - name: git-clone
    taskRef:
      # Use Red Hat provided git-clone task from openshift-pipelines namespace
      # Requires OpenShift Pipelines 1.15+
      resolver: cluster
      params:
        - name: kind
          value: task
        - name: name
          value: git-clone
        - name: namespace
          value: openshift-pipelines
    params:
      - name: URL
        value: $(params.git-url)
      - name: REVISION
        value: $(params.git-revision)
    workspaces:
      - name: output
        workspace: shared-workspace
```

## Git-Clone Task Details

The Red Hat `git-clone` task provides:

- **Repository cloning** with authentication support
- **Sparse checkout** for monorepos
- **Submodule support**
- **SSL verification** options
- **Proxy support**

### Parameters

Key parameters (uppercase in OpenShift Pipelines 1.15+):

| Parameter | Description | Default |
|-----------|-------------|---------|
| `URL` | Git repository URL | (required) |
| `REVISION` | Branch, tag, or SHA | `main` |
| `SUBDIRECTORY` | Clone into subdirectory | `""` |
| `DELETE_EXISTING` | Clean workspace before clone | `true` |
| `DEPTH` | Git clone depth (0=full history) | `1` |
| `SSL_VERIFY` | Verify SSL certificates | `true` |
| `SUBMODULES` | Initialize submodules | `true` |
| `VERBOSE` | Enable verbose logging | `false` |

### Workspaces

| Workspace | Description |
|-----------|-------------|
| `output` | Directory to clone into (required) |
| `ssh-directory` | SSH credentials (optional) |
| `basic-auth` | HTTP basic auth (optional) |
| `ssl-ca-directory` | Custom CA certificates (optional) |

### Results

The task produces these results:

| Result | Description |
|--------|-------------|
| `COMMIT` | SHA of the cloned commit |
| `URL` | Precise repository URL |
| `COMMITTER_DATE` | Epoch timestamp of commit |

**Note:** In OpenShift Pipelines 1.15, there's a known issue where the COMMIT result is not set when using the cluster resolver. This does not affect the ClusterTask version (if still using deprecated ClusterTasks).

## Troubleshooting

### Task Not Found

**Error:**
```
error: tasks.tekton.dev "git-clone" not found in namespace openshift-pipelines
```

**Solution:**

1. Check OpenShift Pipelines operator is installed:
   ```bash
   oc get subscription -n openshift-operators openshift-pipelines-operator
   ```

2. Verify tasks are available:
   ```bash
   oc get task -n openshift-pipelines
   ```

3. Check operator version (should be 1.15+):
   ```bash
   oc get csv -n openshift-operators | grep pipelines
   ```

### Cluster Resolver Not Available

**Error:**
```
error: cluster resolver not found
```

**Solution:**

Ensure you're using OpenShift Pipelines 1.15 or later. The cluster resolver was introduced in Tekton Pipelines 0.41.0 (included in OpenShift Pipelines 1.9+).

### Version Compatibility

Different OpenShift Pipelines versions include different task versions:

- **1.15+**: Uses Tasks in openshift-pipelines namespace (cluster resolver)
- **1.14 and earlier**: Uses ClusterTasks (deprecated)

Check your operator version:

```bash
oc get csv -n openshift-operators | grep pipelines
```

For OpenShift Pipelines 1.15+:
- Tasks use RHEL9-based images
- Parameters are UPPERCASE (e.g., `URL` instead of `url`)
- Tasks are in `openshift-pipelines` namespace

## Best Practices

1. **Always use Red Hat provided tasks** - Don't create custom git-clone tasks
2. **Use cluster resolver** - Reference tasks via cluster resolver for maintainability
3. **Version awareness** - Check task version matches your needs
4. **Uppercase parameters** - Use uppercase parameter names (OpenShift Pipelines 1.15+)
5. **Test upgrades** - Verify pipelines work after operator upgrades

## Additional Resources

- [OpenShift Pipelines 1.22 Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_pipelines/1.22/html/about_openshift_pipelines/understanding-openshift-pipelines)
- [git-clone Task Documentation](https://github.com/openshift-pipelines/task-git/blob/main/docs/task-git-clone.md)
- [Tekton Resolvers Documentation](https://tekton.dev/docs/pipelines/resolution/)

## Related Files

- `chart/templates/pipeline-deploy-kfp.yaml` - Pipeline definition using git-clone task
- `chart/values.yaml` - Configuration values
