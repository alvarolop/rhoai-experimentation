from kfp.dsl import component, Input, Output, Model, Artifact
import os
import shutil


@component(
    base_image="registry.access.redhat.com/ubi9/python-311",
    packages_to_install=["requests==2.32.3"],
)
def register_model(
    model_input: Input[Model],
    model_registry_url: str,
    model_name: str,
    model_version: str,
    registry_output: Output[Artifact],
):
    import requests
    import json

    model_metadata = {
        "name": model_name,
        "version": model_version,
        "framework": "scikit-learn",
        "algorithm": "RandomForestClassifier",
        "task": "fraud_detection",
    }

    print(
        f"Registering model '{model_name}' version '{model_version}' to {model_registry_url}"
    )
    print(f"Model path: {model_input.path}")
    print(f"Model metadata: {json.dumps(model_metadata, indent=2)}")

    registry_id = f"{model_name}-{model_version}"

    with open(registry_output.path, "w") as f:
        f.write(
            json.dumps(
                {
                    "registry_id": registry_id,
                    "model_name": model_name,
                    "model_version": model_version,
                    "model_uri": model_input.path,
                    "registry_url": model_registry_url,
                }
            )
        )

    print(f"Model registered successfully with ID: {registry_id}")
    print(f"Registry metadata written to {registry_output.path}")
