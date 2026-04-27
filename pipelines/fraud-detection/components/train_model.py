from kfp.dsl import component, Input, Output, Dataset, Model, Metrics
import pandas as pd
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


@component(
    base_image="python:3.11-slim",
    packages_to_install=["pandas==2.2.2", "scikit-learn==1.5.0"]
)
def train_fraud_model(
    input_data: Input[Dataset],
    model_output: Output[Model],
    metrics: Output[Metrics],
    test_size: float = 0.2,
    n_estimators: int = 100
):
    df = pd.read_csv(input_data.path)

    X = df.drop('is_fraud', axis=1)
    y = df['is_fraud']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=10,
        random_state=42,
        class_weight='balanced'
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)

    print(f"Model Performance:")
    print(f"  Accuracy:  {accuracy:.4f}")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1 Score:  {f1:.4f}")

    metrics.log_metric("accuracy", accuracy)
    metrics.log_metric("precision", precision)
    metrics.log_metric("recall", recall)
    metrics.log_metric("f1_score", f1)

    with open(model_output.path, 'wb') as f:
        pickle.dump(clf, f)

    print(f"Model saved to {model_output.path}")
