# Fraud Detection Pipeline

Complete ML pipeline demonstrating RHOAI capabilities with real components (no mocks).

## Pipeline Steps

```
1. Validate Pipeline
   ↓
2. Generate Data
   ↓
3. Train Model
   ↓
4. Register in Model Registry
   ↓
5. Export to ONNX & Upload to S3
   ↓
6. Deploy with OpenVINO
   ↓
7. Configure TrustyAI Monitoring
```

## Components

### 1. Validate Pipeline
**File:** `components/validate_pipeline.py`

Validates prerequisites before pipeline execution:
- S3 endpoint connectivity
- Model Registry API accessibility  
- Namespace verification

**Why?** Fail fast if infrastructure isn't ready.

### 2. Generate Fraud Data
**File:** `components/data_generator.py`

Generates synthetic credit card transaction data:
- 10,000 samples (configurable)
- ~2% fraud rate (realistic ratio)
- Features: amount, time, location, merchant type

**Output:** CSV dataset with fraud labels

### 3. Train Model
**File:** `components/train_model.py`

Trains RandomForestClassifier:
- Stratified train/test split
- Class-balanced weighting (handles imbalance)
- Logs metrics: accuracy, precision, recall, F1

**Output:**
- Trained model (pickle format)
- Performance metrics
- Model metadata (JSON)

### 4. Register Model
**File:** `components/register_model_real.py`

Registers model in RHOAI Model Registry via REST API:
- Creates/updates RegisteredModel
- Creates ModelVersion with metadata
- Stores performance metrics as custom properties

**Why Model Registry?**
- Version tracking
- Metadata management
- Lineage and governance

### 5. Export to ONNX & Upload to S3
**File:** `components/export_to_s3.py`

Converts and uploads model:
- sklearn → ONNX (portable format)
- Upload to S3/MinIO storage
- Saves model + metadata

**Why ONNX?**
- Runtime-agnostic format
- Optimized for inference
- Supported by OpenVINO

### 6. Deploy with OpenVINO
**File:** `components/deploy_openvino.py`

Creates KServe InferenceService:
- Runtime: `kserve-ovms` (OpenVINO Model Server)
- Model format: ONNX
- Storage: S3
- Resource limits: 1 CPU, 2Gi memory

**Why OpenVINO?**
- Optimized for Intel CPUs
- Fast inference on CPU
- Lower resource requirements than GPU

**Deployment mode:** RawDeployment (Serverless available too)

### 7. Configure TrustyAI Monitoring
**File:** `components/configure_trustyai.py`

Sets up bias and fairness monitoring:
- Creates TrustyAIService (if needed)
- Creates InferenceServiceMonitor
- Enables metrics: SPD, DIR

**Metrics:**
- **SPD** (Statistical Parity Difference): Bias detection
- **DIR** (Disparate Impact Ratio): Fairness measure

**Dashboard:** `http://trustyai-service.{namespace}.svc.cluster.local/q/metrics`

## Pipeline Parameters

### Data Generation
- `num_samples` (int): Number of transactions to generate (default: 10000)
- `fraud_ratio` (float): Percentage of fraudulent transactions (default: 0.02)
- `test_size` (float): Test set proportion (default: 0.2)

### Model Training
- `n_estimators` (int): RandomForest trees (default: 100)

### Model Metadata
- `model_name` (str): Model identifier (default: "fraud-detector")
- `model_version` (str): Version tag (default: "v1")
- `model_registry_url` (str): Model Registry endpoint

### S3 Configuration
- `s3_endpoint` (str): MinIO/S3 endpoint
- `s3_bucket` (str): Bucket name (default: "models")
- `s3_access_key` (str): Access key
- `s3_secret_key` (str): Secret key

### Deployment
- `namespace` (str): Target namespace
- `enable_trustyai` (bool): Enable monitoring (default: true)

## Running the Pipeline

### Prerequisites

1. **Data Science Pipelines** server running
2. **Model Registry** deployed and accessible
3. **S3/MinIO** storage configured
4. **KServe** operator installed
5. **TrustyAI** operator installed (optional, for monitoring)

### Via RHOAI UI

1. Navigate to Data Science Pipelines
2. Import `fraud_detection_pipeline.yaml`
3. Create Run
4. Configure parameters
5. Submit

### Via CLI (kfp)

```python
import kfp

client = kfp.Client(host='https://ds-pipeline-dspa.namespace.svc:8443')

# Run with defaults
run = client.create_run_from_pipeline_package(
    'fraud_detection_pipeline.yaml',
    arguments={},
    experiment_name='fraud-detection'
)

# Run with custom parameters
run = client.create_run_from_pipeline_package(
    'fraud_detection_pipeline.yaml',
    arguments={
        'num_samples': 50000,
        'model_version': 'v2',
        'n_estimators': 200
    },
    experiment_name='fraud-detection'
)
```

### Via Tekton (CI/CD)

The Helm chart includes automated Tekton pipeline:

```bash
# Trigger via Tekton
oc create -f tekton/example-run.yaml
```

See [../../tekton/README.md](../../tekton/README.md)

## Model Deployment

After successful pipeline run:

### Inference Service

**Name:** `fraud-detector-v1` (based on model_name + model_version)

**Predictor URL:**
```
http://fraud-detector-v1-predictor.{namespace}.svc.cluster.local/v2/models/fraud-detector-v1/infer
```

### Test Inference

```bash
# Port-forward to predictor
oc port-forward svc/fraud-detector-v1-predictor 8080:80

# Send test request (V2 protocol)
curl -X POST http://localhost:8080/v2/models/fraud-detector-v1/infer \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": [{
      "name": "input",
      "shape": [1, 8],
      "datatype": "FP32",
      "data": [
        [100.5, 14, 3, 1, 0, 0, 0, 15.2]
      ]
    }]
  }'
```

**Expected response:**
```json
{
  "outputs": [{
    "name": "output",
    "shape": [1, 1],
    "datatype": "FP32",
    "data": [0]
  }]
}
```

## TrustyAI Monitoring

### Access Metrics

```bash
# Port-forward TrustyAI service
oc port-forward svc/trustyai-service 8080:80

# View metrics dashboard
open http://localhost:8080/q/metrics
```

### Available Metrics

- **SPD** (Statistical Parity Difference)
  - Measures fairness across protected groups
  - Range: [-1, 1], closer to 0 is better

- **DIR** (Disparate Impact Ratio)
  - Ratio of positive outcomes between groups
  - Range: [0, ∞], 1.0 is perfect fairness

## Troubleshooting

### Pipeline Validation Fails

**Error:** `S3 endpoint unreachable`

**Solution:** Check MinIO is running:
```bash
oc get pod -l app=minio
oc logs -l app=minio
```

### Model Registry Connection Issues

**Error:** `Model Registry unreachable`

**Solution:** Verify Model Registry service:
```bash
oc get svc model-registry-service
curl http://model-registry-service:8080/api/model_registry/v1alpha3/registered_models
```

### ONNX Conversion Fails

**Error:** `ONNX conversion failed`

**Cause:** Unsupported sklearn operation

**Solution:** Check sklearn version matches (1.7.0) and model uses supported operations

### Deployment Fails

**Error:** `InferenceService not ready`

**Solution:** Check KServe controller logs:
```bash
oc logs -n redhat-ods-applications -l control-plane=kserve-controller-manager
```

Check predictor pod:
```bash
oc get pod -l serving.kserve.io/inferenceservice=fraud-detector-v1
oc logs fraud-detector-v1-predictor-xxx
```

### TrustyAI Not Available

**Error:** `TrustyAI configuration failed`

**Solution:** Install TrustyAI operator:
```bash
oc get csv -n redhat-ods-applications | grep trustyai
```

If not installed, TrustyAI steps will be skipped (pipeline continues).

## Performance

### Pipeline Execution Time

| Step | Duration | Notes |
|------|----------|-------|
| Validate | 5-10s | Quick checks |
| Generate Data | 10-20s | 10k samples |
| Train Model | 30-60s | 100 trees |
| Register Model | 5-10s | API calls |
| Export to ONNX | 10-15s | Conversion + upload |
| Deploy OpenVINO | 30-60s | Pod creation |
| Configure TrustyAI | 10-20s | CRD creation |
| **Total** | **~2-4 min** | End-to-end |

### Resource Usage

| Component | CPU | Memory |
|-----------|-----|--------|
| Pipeline pods | 100m-500m | 256Mi-1Gi |
| Predictor | 100m-1 | 256Mi-2Gi |
| TrustyAI | 100m | 256Mi |

## Next Steps

1. **Experiment with parameters:**
   - Try different `n_estimators` values
   - Adjust `fraud_ratio` for different scenarios
   - Test with larger datasets

2. **Improve the model:**
   - Add feature engineering component
   - Try different algorithms (XGBoost, etc.)
   - Implement hyperparameter tuning

3. **Production readiness:**
   - Add model validation step
   - Implement A/B testing
   - Set up alerting on TrustyAI metrics
   - Add data drift detection

4. **Scale deployment:**
   - Enable autoscaling (HPA)
   - Test with production load
   - Implement canary deployments

## Related Documentation

- [RHOAI Data Science Pipelines](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.3/html/working_with_data_science_pipelines/index)
- [KServe OpenVINO Runtime](https://kserve.github.io/website/latest/modelserving/v1beta1/openvino/)
- [TrustyAI Metrics](https://trustyai-explainability.github.io/trustyai-site/main/trustyai-service-operator/)
- [Model Registry](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.3/html/managing_model_registries/index)
