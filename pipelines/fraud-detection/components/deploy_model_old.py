from kfp.dsl import component, Input, Output, Artifact
import time


@component(
    base_image="registry.access.redhat.com/ubi9/python-311",
    packages_to_install=["requests==2.32.3"],
)
def deploy_model(
    registry_info: Input[Artifact], namespace: str, endpoint_output: Output[Artifact]
):
    import json

    with open(registry_info.path, "r") as f:
        registry_data = json.load(f)

    model_name = registry_data["model_name"]
    model_version = registry_data["model_version"]
    model_uri = registry_data["model_uri"]

    inference_service_name = f"{model_name}-{model_version}".replace("_", "-").lower()

    print(f"Deploying model '{model_name}' version '{model_version}'")
    print(f"InferenceService name: {inference_service_name}")
    print(f"Namespace: {namespace}")
    print(f"Model URI: {model_uri}")

    endpoint_url = f"http://{inference_service_name}-predictor.{namespace}.svc.cluster.local/v2/models/{inference_service_name}/infer"

    print(f"Simulating deployment to KServe...")
    time.sleep(2)

    with open(endpoint_output.path, "w") as f:
        f.write(
            json.dumps(
                {
                    "endpoint_url": endpoint_url,
                    "inference_service_name": inference_service_name,
                    "namespace": namespace,
                    "status": "Ready",
                }
            )
        )

    print(f"Model deployed successfully")
    print(f"Inference endpoint: {endpoint_url}")
