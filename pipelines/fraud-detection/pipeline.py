from kfp import dsl
from components.data_generator import generate_fraud_data
from components.train_model import train_fraud_model


@dsl.pipeline(
    name="Fraud Detection ML Pipeline",
    description="Simplified ML pipeline for testing: generate data and train model",
)
def fraud_detection_pipeline(
    # Data generation
    num_samples: int = 1000,  # Reduced for faster testing
    fraud_ratio: float = 0.02,
    # Model training
    test_size: float = 0.2,
    n_estimators: int = 10,  # Reduced for faster testing
):
    """
    Simplified fraud detection pipeline for testing in disconnected environments.

    Steps:
    1. Generate synthetic fraud detection data
    2. Train RandomForest model

    Note: Model registration, S3 export, deployment, and monitoring are disabled
    for initial testing. Enable them in production once the base pipeline works.
    """

    # Step 1: Generate synthetic fraud data
    generate_task = generate_fraud_data(
        num_samples=num_samples, fraud_ratio=fraud_ratio
    )

    # Step 2: Train fraud detection model
    train_task = train_fraud_model(
        input_data=generate_task.outputs["output_data"],
        test_size=test_size,
        n_estimators=n_estimators,
    )


if __name__ == "__main__":
    from kfp import compiler

    compiler.Compiler().compile(
        pipeline_func=fraud_detection_pipeline,
        package_path="fraud_detection_pipeline.yaml",
    )
    print("✅ Pipeline compiled successfully to fraud_detection_pipeline.yaml")
