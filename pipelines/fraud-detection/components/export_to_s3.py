from kfp.dsl import component, Input, Output, Model, Artifact


@component(
    # Custom image with pre-installed ML libraries for disconnected environments
    base_image="quay.io/alopezme/rhoai-experimentation-kfp:latest",
    # packages_to_install=[
    #     "scikit-learn==1.7.0",
    #     "skl2onnx==1.18.0",
    #     "onnx==1.17.0",
    #     "boto3==1.37.0",
    # ],  # Pre-installed in custom image
)
def export_to_s3(
    model_input: Input[Model],
    model_metadata: str,
    s3_endpoint: str,
    s3_bucket: str,
    s3_access_key: str,
    s3_secret_key: str,
    model_name: str,
    model_version: str,
    s3_output: Output[Artifact],
) -> str:
    """
    Convert sklearn model to ONNX and upload to S3.
    Returns S3 URI of the uploaded model.
    """
    import pickle
    import json
    import boto3
    from skl2onnx import to_onnx
    import numpy as np

    print("=" * 60)
    print("Export Model to ONNX and Upload to S3")
    print("=" * 60)

    metadata = json.loads(model_metadata)

    # Load sklearn model
    print(f"\nOK Loading model from {model_input.path}...")
    with open(model_input.path, "rb") as f:
        sklearn_model = pickle.load(f)
    print(f"  OK Loaded {metadata.get('model_type', 'model')}")

    # Convert to ONNX
    print(f"\nOK Converting to ONNX format...")
    n_features = metadata.get("n_features", 8)

    # Create dummy input for ONNX conversion
    initial_type = [("input", "float", [None, n_features])]

    try:
        onnx_model = to_onnx(sklearn_model, initial_types=initial_type, target_opset=15)
        print(f"  OK Converted to ONNX (opset 15)")
    except Exception as e:
        print(f"  ERROR ONNX conversion failed: {e}")
        raise

    # Save ONNX locally first
    onnx_path = f"/tmp/{model_name}-{model_version}.onnx"
    with open(onnx_path, "wb") as f:
        f.write(onnx_model.SerializeToString())
    print(f"  OK Saved locally to {onnx_path}")

    # Upload to S3
    print(f"\nOK Uploading to S3...")
    s3_key = f"models/{model_name}/{model_version}/model.onnx"

    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=f"http://{s3_endpoint}",
            aws_access_key_id=s3_access_key,
            aws_secret_access_key=s3_secret_key,
        )

        # Create bucket if it doesn't exist
        try:
            s3_client.head_bucket(Bucket=s3_bucket)
            print(f"  OK Bucket '{s3_bucket}' exists")
        except:
            print(f"  OK Creating bucket '{s3_bucket}'...")
            s3_client.create_bucket(Bucket=s3_bucket)

        # Upload model
        s3_client.upload_file(onnx_path, s3_bucket, s3_key)
        s3_uri = f"s3://{s3_bucket}/{s3_key}"
        print(f"  OK Uploaded to {s3_uri}")

        # Also upload metadata
        metadata_key = f"models/{model_name}/{model_version}/metadata.json"
        s3_client.put_object(
            Bucket=s3_bucket, Key=metadata_key, Body=json.dumps(metadata, indent=2)
        )
        print(f"  OK Uploaded metadata to s3://{s3_bucket}/{metadata_key}")

    except Exception as e:
        print(f"  ERROR S3 upload failed: {e}")
        s3_uri = f"local://{onnx_path}"
        print(f"  WARNING  Using local path instead")

    # Save S3 info
    s3_info = {
        "s3_uri": s3_uri,
        "s3_bucket": s3_bucket,
        "s3_key": s3_key,
        "model_format": "onnx",
        "model_name": model_name,
        "model_version": model_version,
    }

    with open(s3_output.path, "w") as f:
        json.dump(s3_info, f, indent=2)

    print(f"\nOK S3 info saved to {s3_output.path}")
    print("=" * 60)

    return s3_uri
