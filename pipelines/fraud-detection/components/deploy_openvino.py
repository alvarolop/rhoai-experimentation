from kfp.dsl import component, Input, Output, Artifact


@component(
    # Custom image with pre-installed ML libraries for disconnected environments
    base_image="quay.io/alopezme/rhoai-experimentation-kfp:latest",
    # packages_to_install=["kubernetes==31.0.0"],  # Pre-installed in custom image
)
def deploy_openvino(
    s3_info_input: Input[Artifact],
    model_name: str,
    model_version: str,
    namespace: str,
    deployment_output: Output[Artifact],
) -> str:
    """
    Deploy ONNX model to KServe with OpenVINO runtime.
    Returns InferenceService name.
    """
    import json
    from kubernetes import client, config

    print("=" * 60)
    print("Deploy Model with OpenVINO Runtime")
    print("=" * 60)

    # Load S3 info
    with open(s3_info_input.path, "r") as f:
        s3_info = json.load(f)

    s3_uri = s3_info["s3_uri"]
    print(f"\nOK Model location: {s3_uri}")

    # Generate InferenceService name (DNS-1123 compliant)
    isvc_name = f"{model_name}-{model_version}".replace("_", "-").lower()
    if len(isvc_name) > 63:
        isvc_name = isvc_name[:63].rstrip("-")

    print(f"OK InferenceService name: {isvc_name}")

    # Create InferenceService manifest
    inference_service = {
        "apiVersion": "serving.kserve.io/v1beta1",
        "kind": "InferenceService",
        "metadata": {
            "name": isvc_name,
            "namespace": namespace,
            "annotations": {
                "serving.kserve.io/deploymentMode": "RawDeployment",
                "openshift.io/display-name": f"Fraud Detection Model {model_version}",
                "serving.kserve.io/enable-prometheus-scraping": "true",
            },
            "labels": {
                "app": "fraud-detection",
                "model": model_name,
                "version": model_version,
                "runtime": "openvino",
            },
        },
        "spec": {
            "predictor": {
                "model": {
                    "modelFormat": {"name": "onnx", "version": "1"},
                    "runtime": "kserve-ovms",  # OpenVINO Model Server
                    "storageUri": s3_uri,
                    "resources": {
                        "requests": {"cpu": "100m", "memory": "256Mi"},
                        "limits": {"cpu": "1", "memory": "2Gi"},
                    },
                }
            }
        },
    }

    print(f"\nOK Creating InferenceService...")

    try:
        # Load in-cluster config
        config.load_incluster_config()

        # Create custom object API client
        api = client.CustomObjectsApi()

        # Check if InferenceService already exists
        try:
            existing = api.get_namespaced_custom_object(
                group="serving.kserve.io",
                version="v1beta1",
                namespace=namespace,
                plural="inferenceservices",
                name=isvc_name,
            )
            print(f"  OK InferenceService '{isvc_name}' already exists, updating...")

            # Update existing
            api.patch_namespaced_custom_object(
                group="serving.kserve.io",
                version="v1beta1",
                namespace=namespace,
                plural="inferenceservices",
                name=isvc_name,
                body=inference_service,
            )
            print(f"  OK Updated InferenceService '{isvc_name}'")

        except client.exceptions.ApiException as e:
            if e.status == 404:
                # Create new
                api.create_namespaced_custom_object(
                    group="serving.kserve.io",
                    version="v1beta1",
                    namespace=namespace,
                    plural="inferenceservices",
                    body=inference_service,
                )
                print(f"  OK Created InferenceService '{isvc_name}'")
            else:
                raise

        # Predictor endpoint
        predictor_url = f"http://{isvc_name}-predictor.{namespace}.svc.cluster.local/v2/models/{isvc_name}/infer"

    except Exception as e:
        print(f"  ERROR Deployment failed: {e}")
        print(f"  WARNING  Creating deployment manifest only...")
        predictor_url = f"http://{isvc_name}-predictor.{namespace}.svc.cluster.local/v2/models/{isvc_name}/infer"

    # Save deployment info
    deployment_info = {
        "inference_service_name": isvc_name,
        "namespace": namespace,
        "predictor_url": predictor_url,
        "runtime": "kserve-ovms",
        "model_format": "onnx",
        "model_name": model_name,
        "model_version": model_version,
        "s3_uri": s3_uri,
    }

    with open(deployment_output.path, "w") as f:
        json.dump(deployment_info, f, indent=2)

    print(f"\nOK Deployment info saved")
    print(f"OK Predictor URL: {predictor_url}")
    print("=" * 60)

    return isvc_name
