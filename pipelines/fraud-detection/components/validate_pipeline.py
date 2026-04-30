from kfp.dsl import component


@component(
    # Custom image with pre-installed ML libraries for disconnected environments
    base_image="quay.io/alopezme/rhoai-experimentation-kfp:latest",
    # packages_to_install=["requests==2.32.3"],  # Pre-installed in custom image
)
def validate_pipeline(
    s3_endpoint: str, s3_bucket: str, model_registry_url: str, namespace: str
):
    """
    Validate pipeline prerequisites and configuration.
    Checks connectivity to required services.
    """
    import requests
    import sys

    errors = []

    print("=" * 60)
    print("Pipeline Validation")
    print("=" * 60)

    # Validate S3 connectivity
    print(f"\n✓ Checking S3 endpoint: {s3_endpoint}")
    try:
        # Just check if endpoint is reachable (MinIO or AWS S3)
        response = requests.get(f"http://{s3_endpoint}/minio/health/live", timeout=5)
        if response.status_code == 200:
            print(f"  ✅ S3 endpoint reachable")
        else:
            print(f"  ⚠️  S3 endpoint returned {response.status_code}")
    except Exception as e:
        errors.append(f"S3 endpoint unreachable: {e}")
        print(f"  ❌ S3 endpoint unreachable: {e}")

    # Validate Model Registry connectivity
    print(f"\n✓ Checking Model Registry: {model_registry_url}")
    try:
        response = requests.get(
            f"{model_registry_url}/api/model_registry/v1alpha3/registered_models",
            timeout=5,
        )
        if response.status_code == 200:
            print(f"  ✅ Model Registry accessible")
        else:
            print(f"  ⚠️  Model Registry returned {response.status_code}")
    except Exception as e:
        errors.append(f"Model Registry unreachable: {e}")
        print(f"  ❌ Model Registry unreachable: {e}")

    # Validate namespace
    print(f"\n✓ Checking namespace: {namespace}")
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as f:
            current_ns = f.read().strip()
        print(f"  ✅ Running in namespace: {current_ns}")
        if current_ns != namespace:
            print(f"  ⚠️  Warning: Expected {namespace}, running in {current_ns}")
    except Exception as e:
        print(f"  ⚠️  Could not verify namespace: {e}")

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print("❌ Validation FAILED with errors:")
        for err in errors:
            print(f"  - {err}")
        print("=" * 60)
        sys.exit(1)
    else:
        print("✅ All validations PASSED")
        print("=" * 60)
