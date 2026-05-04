from kfp.dsl import component, Input, Output, Model, Artifact


@component(
    # Custom image with pre-installed ML libraries for disconnected environments
    base_image="quay.io/alopezme/rhoai-experimentation-kfp:latest",
    # packages_to_install=["requests==2.32.3"],  # Pre-installed in custom image
)
def register_model_real(
    model_input: Input[Model],
    model_metadata: str,
    model_registry_url: str,
    model_name: str,
    model_version: str,
    registry_output: Output[Artifact],
) -> str:
    """
    Register model in RHOAI Model Registry using the REST API.
    Returns registered model ID.
    """
    import requests
    import json
    import sys

    print("=" * 60)
    print("Registering Model in Model Registry")
    print("=" * 60)

    metadata = json.loads(model_metadata)

    # Create RegisteredModel if it doesn't exist
    print(f"\nOK Checking RegisteredModel '{model_name}'...")

    registered_model_payload = {
        "name": model_name,
        "description": f"Fraud detection model using {metadata.get('model_type', 'ML')}",
        "customProperties": {
            "framework": {"string_value": "scikit-learn"},
            "task": {"string_value": "classification"},
        },
    }

    try:
        # Try to create RegisteredModel
        response = requests.post(
            f"{model_registry_url}/api/model_registry/v1alpha3/registered_models",
            json=registered_model_payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if response.status_code in [200, 201]:
            registered_model = response.json()
            registered_model_id = registered_model["id"]
            print(f"  OK Created RegisteredModel: {registered_model_id}")
        elif response.status_code == 409:
            # Already exists, get it
            print(f"  OK RegisteredModel already exists, fetching...")
            response = requests.get(
                f"{model_registry_url}/api/model_registry/v1alpha3/registered_models?name={model_name}",
                timeout=10,
            )
            if response.status_code == 200:
                models = response.json().get("items", [])
                if models:
                    registered_model_id = models[0]["id"]
                    print(f"  OK Found RegisteredModel: {registered_model_id}")
                else:
                    raise Exception("RegisteredModel exists but couldn't fetch it")
            else:
                raise Exception(
                    f"Failed to fetch RegisteredModel: {response.status_code}"
                )
        else:
            raise Exception(
                f"Failed to create RegisteredModel: {response.status_code} - {response.text}"
            )

    except Exception as e:
        print(f"  ERROR Model Registry error: {e}")
        print(f"  ⚠️  Continuing with local registration...")
        registered_model_id = f"local-{model_name}"

    # Create ModelVersion
    print(f"\nOK Creating ModelVersion '{model_version}'...")

    model_version_payload = {
        "name": model_version,
        "description": f"Version {model_version} trained with {metadata.get('n_estimators', 'N/A')} estimators",
        "customProperties": {
            "accuracy": {"double_value": metadata.get("accuracy", 0.0)},
            "precision": {"double_value": metadata.get("precision", 0.0)},
            "recall": {"double_value": metadata.get("recall", 0.0)},
            "f1_score": {"double_value": metadata.get("f1_score", 0.0)},
            "n_features": {"int_value": str(metadata.get("n_features", 0))},
            "model_type": {"string_value": metadata.get("model_type", "unknown")},
        },
        "author": "data-science-pipelines",
    }

    try:
        response = requests.post(
            f"{model_registry_url}/api/model_registry/v1alpha3/registered_models/{registered_model_id}/versions",
            json=model_version_payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if response.status_code in [200, 201]:
            model_version_obj = response.json()
            model_version_id = model_version_obj["id"]
            print(f"  OK Created ModelVersion: {model_version_id}")
        else:
            print(f"  ⚠️  ModelVersion creation returned {response.status_code}")
            model_version_id = f"local-{model_version}"

    except Exception as e:
        print(f"  ERROR ModelVersion creation error: {e}")
        model_version_id = f"local-{model_version}"

    # Save registration info
    registration_info = {
        "registered_model_id": registered_model_id,
        "model_version_id": model_version_id,
        "model_name": model_name,
        "model_version": model_version,
        "registry_url": model_registry_url,
        "model_path": model_input.path,
        "metadata": metadata,
    }

    with open(registry_output.path, "w") as f:
        json.dump(registration_info, f, indent=2)

    print(f"\nOK Registration info saved to {registry_output.path}")
    print("=" * 60)

    return model_version_id
