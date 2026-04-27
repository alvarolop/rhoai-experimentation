from kfp import dsl
from components.data_generator import generate_fraud_data
from components.train_model import train_fraud_model
from components.register_model import register_model
from components.deploy_model import deploy_model
from components.benchmark_model import benchmark_model


@dsl.pipeline(
    name="Fraud Detection Pipeline",
    description="End-to-end ML pipeline for fraud detection: data generation, training, registry, deployment, and benchmarking"
)
def fraud_detection_pipeline(
    num_samples: int = 10000,
    fraud_ratio: float = 0.02,
    test_size: float = 0.2,
    n_estimators: int = 100,
    model_name: str = "fraud_detector",
    model_version: str = "v1",
    model_registry_url: str = "http://model-registry-service:8080",
    namespace: str = "rhoai-pipelines-demo",
    num_benchmark_requests: int = 100
):
    generate_task = generate_fraud_data(
        num_samples=num_samples,
        fraud_ratio=fraud_ratio
    )

    train_task = train_fraud_model(
        input_data=generate_task.outputs['output_data'],
        test_size=test_size,
        n_estimators=n_estimators
    )

    register_task = register_model(
        model_input=train_task.outputs['model_output'],
        model_registry_url=model_registry_url,
        model_name=model_name,
        model_version=model_version
    )

    deploy_task = deploy_model(
        registry_info=register_task.outputs['registry_output'],
        namespace=namespace
    )

    benchmark_task = benchmark_model(
        endpoint_info=deploy_task.outputs['endpoint_output'],
        num_requests=num_benchmark_requests
    )


if __name__ == "__main__":
    from kfp import compiler

    compiler.Compiler().compile(
        pipeline_func=fraud_detection_pipeline,
        package_path="fraud_detection_pipeline.yaml"
    )
    print("Pipeline compiled successfully to fraud_detection_pipeline.yaml")
