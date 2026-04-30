from kfp.dsl import component, Input, Output, Dataset, Model, Metrics


@component(
    # Custom image with pre-installed ML libraries for disconnected environments
    base_image="quay.io/alopezme/rhoai-experimentation-kfp:latest",
    # packages_to_install=["pandas==2.3.0", "scikit-learn==1.7.0", "numpy==2.3.0"],  # Pre-installed in custom image
)
def train_fraud_model(
    input_data: Input[Dataset],
    model_output: Output[Model],
    metrics: Output[Metrics],
    test_size: float = 0.2,
    n_estimators: int = 100,
) -> str:
    """
    Train a fraud detection model using RandomForest.
    Returns model metadata as JSON string.
    """
    import pandas as pd
    import pickle
    import json
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

    print("=" * 60)
    print("Training Fraud Detection Model")
    print("=" * 60)

    # Load data
    df = pd.read_csv(input_data.path)
    print(f"\n✓ Loaded dataset: {df.shape[0]} samples, {df.shape[1]} features")

    X = df.drop("is_fraud", axis=1)
    y = df["is_fraud"]

    print(f"  - Fraud samples: {y.sum()} ({y.sum()/len(y)*100:.2f}%)")
    print(
        f"  - Legitimate samples: {(~y.astype(bool)).sum()} ({(~y.astype(bool)).sum()/len(y)*100:.2f}%)"
    )

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )
    print(f"\n✓ Train/test split: {len(X_train)}/{len(X_test)} samples")

    # Train model
    print(f"\n✓ Training RandomForest (n_estimators={n_estimators})...")
    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=10,
        random_state=42,
        class_weight="balanced",
    )
    clf.fit(X_train, y_train)

    # Evaluate
    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    print(f"\n✓ Model Performance:")
    print(f"  - Accuracy:  {accuracy:.4f}")
    print(f"  - Precision: {precision:.4f}")
    print(f"  - Recall:    {recall:.4f}")
    print(f"  - F1 Score:  {f1:.4f}")

    # Log metrics
    metrics.log_metric("accuracy", float(accuracy))
    metrics.log_metric("precision", float(precision))
    metrics.log_metric("recall", float(recall))
    metrics.log_metric("f1_score", float(f1))

    # Save model
    with open(model_output.path, "wb") as f:
        pickle.dump(clf, f)
    print(f"\n✓ Model saved to {model_output.path}")

    # Return metadata
    model_metadata = {
        "model_type": "RandomForestClassifier",
        "n_estimators": n_estimators,
        "n_features": int(X.shape[1]),
        "feature_names": X.columns.tolist(),
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
    }

    print("=" * 60)
    return json.dumps(model_metadata)
