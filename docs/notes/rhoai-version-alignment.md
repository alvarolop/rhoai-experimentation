# RHOAI Version Alignment

## Overview

This demo is aligned with **Red Hat OpenShift AI 3.3.x** (tested on 3.3.0 and 3.3.2) using the **2025.2** workbench image versions (latest recommended).

## Package Versions

Our custom builder image uses the exact same package versions as the official RHOAI workbench images to ensure compatibility.

### RHOAI 3.3.x (2025.2) Workbench Images

**Official Images:**
- `registry.redhat.io/rhoai/odh-workbench-jupyter-datascience-cpu-py312-rhel9:2025.2` ⭐ (recommended)
- `registry.redhat.io/rhoai/odh-workbench-jupyter-tensorflow-cuda-py312-rhel9:2025.2`

**Python Version:** 3.12

**Core ML Libraries:**

| Package | RHOAI 2025.2 | Our Image | Notes |
|---------|--------------|-----------|-------|
| **KFP SDK** | 2.14 | 2.14.0 | ✅ Exact match (latest KFP 2.x) |
| **kfp-kubernetes** | - | 1.3.0 | Added for Kubernetes integration |
| **pandas** | 2.3 | 2.3.0 | ✅ Exact match |
| **numpy** | 2.3 | 2.3.0 | ✅ Exact match |
| **scikit-learn** | 1.7 | 1.7.0 | ✅ Exact match |
| **scipy** | 1.16 | 1.16.0 | ✅ Exact match |
| **matplotlib** | 3.10 | 3.10.0 | ✅ Exact match |
| **requests** | - | 2.32.3 | Standard library |

**Linting Tools (Not in RHOAI workbench):**

| Package | Our Image | Why Added |
|---------|-----------|-----------|
| **pylint** | 3.3.1 | Code quality checks |
| **flake8** | 7.1.1 | Syntax error detection |
| **black** | 24.10.0 | Code formatting enforcement |

## RHOAI Components

### Data Science Pipelines

**Version:** Kubeflow Pipelines 2.5.0

From DataScienceCluster status:
```yaml
datasciencepipelines:
  releases:
  - name: Kubeflow Pipelines
    repoUrl: https://github.com/kubeflow/pipelines
    version: 2.5.0
```

**Compatibility:**
- KFP SDK 2.12 is compatible with KFP backend 2.5.0
- Pipeline YAML format is cross-compatible within KFP 2.x
- DSP API endpoint: `https://ds-pipeline-dspa.<namespace>.svc:8443`

### Model Registry

**Version:** Latest (from upstream)

From DataScienceCluster status:
```yaml
modelregistry:
  releases:
  - name: Kubeflow Model Registry
    repoUrl: https://github.com/kubeflow/model-registry
    version: latest
```

### KServe

**Version:** v0.15

From DataScienceCluster status:
```yaml
kserve:
  releases:
  - name: KServe
    repoUrl: https://github.com/kserve/kserve/
    version: v0.15
```

### Training Operator

**Version:** 1.9.0

From DataScienceCluster status:
```yaml
trainingoperator:
  releases:
  - name: Kubeflow Training Operator
    repoUrl: https://github.com/kubeflow/trainer
    version: 1.9.0
```

## Version Evolution

### RHOAI 3.3.0 → 3.3.2

Both versions support **2025.1** (Python 3.11) and **2025.2** (Python 3.12) workbench images:

| Component | 2025.1 | 2025.2 ⭐ | Recommendation |
|-----------|--------|-----------|----------------|
| Python | 3.11 | 3.12 | Use 2025.2 for latest features |
| KFP SDK | 2.12 | 2.14 | 2.14 recommended (latest KFP 2.x) |
| pandas | 2.2 | 2.3 | 2.3 has performance improvements |
| numpy | 2.2 | 2.3 | 2.3 recommended |
| DSP Backend | 2.5.0 | 2.5.0 | Compatible with both |

**This demo uses 2025.2** (Python 3.12, KFP 2.14) for maximum compatibility and latest features.

### Future: RHOAI 3.4+ (2025.2+)

When upgrading to RHOAI 3.4 or newer with 2025.2 workbench images:

**Expected changes:**
- Python: 3.11 → 3.12
- KFP SDK: 2.12 → 2.14+
- pandas: 2.2 → 2.3
- numpy: 2.2 → 2.3
- scikit-learn: 1.6 → 1.7

**Migration steps:**
1. Update `container-image/Containerfile` with new versions
2. Rebuild and push custom image
3. Update `chart/values.yaml` with new image tag
4. Test pipelines for compatibility

## Verification

### Check Installed RHOAI Version

```bash
# Get RHOAI version
oc get datasciencecluster default-dsc -o jsonpath='{.status.release.version}'
# Output: 3.3.2

# Get operator version
oc get csv -n redhat-ods-operator | grep rhods-operator
```

### Check Workbench Image Versions

```bash
# List all workbench images
oc get imagestream -n redhat-ods-applications

# Check Data Science workbench versions
oc get imagestream s2i-generic-data-science-notebook \
  -n redhat-ods-applications \
  -o jsonpath='{.spec.tags[*].name}' | tr ' ' '\n'

# Get package versions for 2025.1
oc get imagestream s2i-generic-data-science-notebook \
  -n redhat-ods-applications \
  -o jsonpath='{.spec.tags[?(@.name=="2025.1")].annotations.opendatahub\.io/notebook-python-dependencies}' \
  | jq '.'
```

### Verify DSP Backend Version

```bash
# Get DSP version from DataScienceCluster
oc get datasciencecluster default-dsc \
  -o jsonpath='{.status.components.datasciencepipelines.releases[?(@.name=="Kubeflow Pipelines")].version}'
# Output: 2.5.0
```

### Test KFP SDK Compatibility

```python
import kfp

# Create client
client = kfp.Client(host='https://ds-pipeline-dspa.namespace.svc:8443')

# Check version compatibility
print(f"KFP SDK version: {kfp.__version__}")  # Should be 2.12.x

# List experiments (tests API connectivity)
experiments = client.list_experiments()
print(f"Connected to DSP backend successfully")
```

## Disconnected Environments

In disconnected/air-gapped environments:

### Mirror RHOAI Workbench Images

```bash
# Mirror from registry.redhat.io to disconnected registry
skopeo copy \
  docker://registry.redhat.io/rhoai/odh-workbench-jupyter-datascience-cpu-py312-rhel9:2025.2 \
  docker://registry.disconnected.local/rhoai/datascience:2025.2
```

### Custom Image Dependencies

All Python packages in our custom image come from PyPI. For disconnected:

**Option 1:** Build in connected environment, mirror image
```bash
# Build in connected env
podman build -t quay.io/org/rhoai-kfp-builder:latest .

# Mirror to disconnected
skopeo copy \
  docker://quay.io/org/rhoai-kfp-builder:latest \
  docker://registry.disconnected.local/rhoai/kfp-builder:latest
```

**Option 2:** Use internal PyPI mirror

Add to Containerfile:
```dockerfile
RUN pip install --index-url https://pypi.disconnected.local/simple \
    kfp==2.12.0 ...
```

## Troubleshooting

### Version Mismatch Issues

**Symptom:**
```
ImportError: cannot import name 'PipelineSpec' from 'kfp.pipeline_spec'
```

**Cause:** KFP SDK version mismatch

**Solution:**
1. Verify RHOAI version: `oc get datasciencecluster`
2. Check workbench image tag in use
3. Rebuild custom image with matching KFP version

### API Compatibility Issues

**Symptom:**
```
Failed to connect to DSP server: 404 Not Found
```

**Cause:** DSP endpoint URL format changed

**Solution:**
- RHOAI 3.3.x uses: `https://ds-pipeline-dspa.<namespace>.svc:8443`
- Check actual service name: `oc get svc -n <namespace> | grep ds-pipeline`

### Package Dependency Conflicts

**Symptom:**
```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed
```

**Cause:** Incompatible package versions

**Solution:**
Use exact versions from RHOAI workbench images (see table above)

## References

- [RHOAI 3.3 Release Notes](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.3/html/release_notes/index)
- [Data Science Pipelines Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.3/html/working_with_data_science_pipelines/index)
- [Kubeflow Pipelines SDK Documentation](https://kubeflow-pipelines.readthedocs.io/en/stable/)
- [RHOAI Supported Configurations](https://access.redhat.com/articles/rhoai-supported-configs)

## Related Documentation

- [Disconnected Optimization](disconnected-optimization.md)
- [Container Image README](../../container-image/README.md)
- [Using ClusterTasks](using-clustertasks.md)
