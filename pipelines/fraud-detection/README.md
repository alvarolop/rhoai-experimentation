# Fraud Detection Pipeline

This directory contains a complete Kubeflow pipeline for fraud detection using scikit-learn.

## Pipeline Overview

The pipeline demonstrates an end-to-end ML workflow:

1. **Generate Synthetic Data** - Creates a realistic fraud transaction dataset
2. **Train Model** - Trains a RandomForestClassifier on the generated data
3. **Register Model** - Registers the trained model to the Model Registry
4. **Deploy Model** - Creates a KServe InferenceService for serving
5. **Benchmark Model** - Tests the deployed model's performance

## Components

Each component is a self-contained Python function decorated with `@component`:

- `data_generator.py` - Generates synthetic fraud transactions with realistic patterns
- `train_model.py` - Trains and evaluates a scikit-learn classifier
- `register_model.py` - Registers the model with metadata
- `deploy_model.py` - Deploys the model as an InferenceService
- `benchmark_model.py` - Measures inference latency and throughput

## Local Development

### Compile the Pipeline

```bash
cd pipelines/fraud-detection
pip install -r requirements.txt
python pipeline.py
```

This generates `fraud_detection_pipeline.yaml` that can be uploaded to RHOAI Data Science Pipelines.

### Test Components Individually

```python
from components.data_generator import generate_fraud_data

# Components can be tested locally as regular Python functions
```

## Pipeline Parameters

- `num_samples` - Number of transactions to generate (default: 10000)
- `fraud_ratio` - Percentage of fraudulent transactions (default: 0.02)
- `test_size` - Train/test split ratio (default: 0.2)
- `n_estimators` - Number of trees in RandomForest (default: 100)
- `model_name` - Name for the registered model (default: "fraud_detector")
- `model_version` - Version string (default: "v1")
- `model_registry_url` - Model registry endpoint
- `namespace` - Kubernetes namespace for deployment
- `num_benchmark_requests` - Number of requests for benchmarking (default: 100)

## Integration with Tekton

The Tekton pipeline automates:
1. Linting this pipeline code
2. Compiling to YAML
3. Uploading to the Data Science Pipelines server
4. Triggering a pipeline run

See `/tekton/README.md` for details.
