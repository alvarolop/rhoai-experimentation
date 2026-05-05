from kfp.dsl import component, Input, Artifact


@component(
    # Custom image with pre-installed ML libraries for disconnected environments
    base_image="quay.io/alopezme/rhoai-experimentation-kfp:latest",
    # packages_to_install=["kubernetes==31.0.0"],  # Pre-installed in custom image
)
def configure_trustyai(
    deployment_info_input: Input[Artifact], namespace: str, enable_metrics: bool = True
) -> str:
    """
    Configure TrustyAI monitoring for the deployed model.
    Creates TrustyAIService if needed and configures monitoring.
    """
    import json
    from kubernetes import client, config

    print("=" * 60)
    print("Configure TrustyAI Monitoring")
    print("=" * 60)

    # Load deployment info
    with open(deployment_info_input.path, "r") as f:
        deployment_info = json.load(f)

    isvc_name = deployment_info["inference_service_name"]
    print(f"\nOK Model: {isvc_name}")

    if not enable_metrics:
        print("  WARNING  Metrics disabled, skipping TrustyAI configuration")
        return "disabled"

    try:
        # Load in-cluster config
        config.load_incluster_config()
        api = client.CustomObjectsApi()

        # Check if TrustyAIService exists
        trustyai_name = "trustyai-service"
        print(f"\nOK Checking TrustyAIService '{trustyai_name}'...")

        try:
            _ = api.get_namespaced_custom_object(
                group="trustyai.opendatahub.io",
                version="v1alpha1",
                namespace=namespace,
                plural="trustyaiservices",
                name=trustyai_name,
            )
            print("  OK TrustyAIService already exists")

        except client.exceptions.ApiException as e:
            if e.status == 404:
                print("  OK Creating TrustyAIService...")

                # Create TrustyAIService
                trustyai_service = {
                    "apiVersion": "trustyai.opendatahub.io/v1alpha1",
                    "kind": "TrustyAIService",
                    "metadata": {
                        "name": trustyai_name,
                        "namespace": namespace,
                        "labels": {
                            "app": "trustyai",
                            "app.kubernetes.io/name": "trustyai-service",
                        },
                    },
                    "spec": {
                        "storage": {"format": "PVC", "folder": "/data", "size": "1Gi"},
                        "data": {"filename": "data.csv", "format": "CSV"},
                        "metrics": {"schedule": "5s"},
                    },
                }

                api.create_namespaced_custom_object(
                    group="trustyai.opendatahub.io",
                    version="v1alpha1",
                    namespace=namespace,
                    plural="trustyaiservices",
                    body=trustyai_service,
                )
                print("  OK Created TrustyAIService")
            else:
                raise

        # Create InferenceServiceMonitor for the model
        print(f"\nOK Configuring monitoring for '{isvc_name}'...")

        monitor_name = f"{isvc_name}-monitor"

        # InferenceServiceMonitor configuration
        monitor = {
            "apiVersion": "trustyai.opendatahub.io/v1alpha1",
            "kind": "InferenceServiceMonitor",
            "metadata": {
                "name": monitor_name,
                "namespace": namespace,
                "labels": {
                    "model": deployment_info["model_name"],
                    "version": deployment_info["model_version"],
                },
            },
            "spec": {
                "inferenceService": {"name": isvc_name, "namespace": namespace},
                "storage": {"format": "PVC"},
                "metrics": [
                    {
                        "name": "SPD",  # Statistical Parity Difference
                        "enabled": True,
                        "batchSize": 100,
                    },
                    {
                        "name": "DIR",  # Disparate Impact Ratio
                        "enabled": True,
                        "batchSize": 100,
                    },
                ],
            },
        }

        try:
            # Try to create monitor
            api.create_namespaced_custom_object(
                group="trustyai.opendatahub.io",
                version="v1alpha1",
                namespace=namespace,
                plural="inferenceservicemonitors",
                body=monitor,
            )
            print(f"  OK Created InferenceServiceMonitor '{monitor_name}'")

        except client.exceptions.ApiException as e:
            if e.status == 409:
                print(f"  OK InferenceServiceMonitor '{monitor_name}' already exists")
            else:
                print(f"  WARNING  Monitor creation returned {e.status}: {e.reason}")

        # Get TrustyAI service endpoint
        trustyai_url = f"http://trustyai-service.{namespace}.svc.cluster.local"
        print(f"\nOK TrustyAI Service URL: {trustyai_url}")
        print(f"OK Metrics dashboard: {trustyai_url}/q/metrics")

    except Exception as e:
        print(f"  ERROR TrustyAI configuration failed: {e}")
        print("  WARNING  Model deployed without monitoring")
        return "failed"

    print("=" * 60)
    return "configured"
