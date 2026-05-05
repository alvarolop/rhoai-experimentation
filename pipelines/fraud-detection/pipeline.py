from kfp import dsl
from components.validate_pipeline import validate_pipeline
from components.data_generator import generate_fraud_data
from components.train_model import train_fraud_model
from components.register_model_real import register_model_real
from components.export_to_s3 import export_to_s3
from components.deploy_openvino import deploy_openvino
from components.configure_trustyai import configure_trustyai


@dsl.pipeline(
    name="Fraud Detection ML Pipeline",
    description="Complete ML pipeline: validate, train, register, export to S3, deploy with OpenVINO, monitor with TrustyAI",
)
def fraud_detection_pipeline(
    # Data generation
    num_samples: int = 10000,
    fraud_ratio: float = 0.02,
    test_size: float = 0.2,
    # Model training
    n_estimators: int = 100,
    # Model registration
    model_name: str = "fraud-detector",
    model_version: str = "v1",
    model_registry_url: str = "http://local.rhoai-model-registries.svc.cluster.local:8080",
    # S3 configuration
    s3_endpoint: str = "minio.minio.svc.cluster.local:9000",
    s3_bucket: str = "models",
    s3_access_key: str = "minio",
    s3_secret_key: str = "minio123",
    # Deployment
    namespace: str = "rhoai-playground",
    # Monitoring
    enable_trustyai: bool = True,
):
    """
    End-to-end fraud detection pipeline with OpenVINO deployment and TrustyAI monitoring.

    Steps:
    1. Validate pipeline prerequisites (S3, Model Registry connectivity)
    2. Generate synthetic fraud detection data
    3. Train RandomForest model
    4. Register model in Model Registry
    5. Convert to ONNX and upload to S3
    6. Deploy with OpenVINO runtime on KServe
    7. Configure TrustyAI monitoring for bias detection
    """

    # Step 1: Validate pipeline configuration
    validate_task = validate_pipeline(
        s3_endpoint=s3_endpoint,
        s3_bucket=s3_bucket,
        model_registry_url=model_registry_url,
        namespace=namespace,
    )

    # Step 2: Generate synthetic fraud data
    generate_task = generate_fraud_data(
        num_samples=num_samples, fraud_ratio=fraud_ratio
    )
    generate_task.after(validate_task)

    # Step 3: Train fraud detection model
    train_task = train_fraud_model(
        input_data=generate_task.outputs["output_data"],
        test_size=test_size,
        n_estimators=n_estimators,
    )

    # Step 4: Export to ONNX and upload to S3 (before registering so we have S3 location)
    export_task = export_to_s3(
        model_input=train_task.outputs["model_output"],
        model_metadata=train_task.outputs[
            "Output"
        ],  # Return value from train_fraud_model
        s3_endpoint=s3_endpoint,
        s3_bucket=s3_bucket,
        s3_access_key=s3_access_key,
        s3_secret_key=s3_secret_key,
        model_name=model_name,
        model_version=model_version,
    )

    # Step 5: Register model in Model Registry (with S3 location from export)
    _ = register_model_real(
        model_input=train_task.outputs["model_output"],
        model_metadata=train_task.outputs[
            "Output"
        ],  # Return value from train_fraud_model
        model_registry_url=model_registry_url,
        model_name=model_name,
        model_version=model_version,
        s3_info_input=export_task.outputs["s3_output"],  # S3 info artifact from export
    )

    # Step 6: Deploy with OpenVINO runtime
    deploy_task = deploy_openvino(
        s3_info_input=export_task.outputs["s3_output"],
        model_name=model_name,
        model_version=model_version,
        namespace=namespace,
    )

    # Step 7: Configure TrustyAI monitoring
    _ = configure_trustyai(
        deployment_info_input=deploy_task.outputs["deployment_output"],
        namespace=namespace,
        enable_metrics=enable_trustyai,
    )


if __name__ == "__main__":
    from kfp import compiler

    compiler.Compiler().compile(
        pipeline_func=fraud_detection_pipeline,
        package_path="fraud_detection_pipeline.yaml",
    )
    print("OK Pipeline compiled successfully to fraud_detection_pipeline.yaml")
