from kfp.dsl import component, Output, Dataset
import pandas as pd
import numpy as np


@component(
    base_image="registry.access.redhat.com/ubi9/python-311",
    packages_to_install=["pandas==2.2.2", "numpy==1.26.4"]
)
def generate_fraud_data(
    output_data: Output[Dataset],
    num_samples: int = 10000,
    fraud_ratio: float = 0.02
):
    np.random.seed(42)

    num_fraud = int(num_samples * fraud_ratio)
    num_legitimate = num_samples - num_fraud

    legitimate_transactions = {
        'amount': np.random.lognormal(3.5, 1.5, num_legitimate),
        'hour': np.random.randint(6, 22, num_legitimate),
        'day_of_week': np.random.randint(0, 7, num_legitimate),
        'merchant_category': np.random.choice(['retail', 'food', 'gas', 'online'], num_legitimate, p=[0.3, 0.3, 0.2, 0.2]),
        'distance_from_home': np.random.gamma(2, 10, num_legitimate),
        'is_fraud': np.zeros(num_legitimate, dtype=int)
    }

    fraud_transactions = {
        'amount': np.random.lognormal(5.0, 2.0, num_fraud),
        'hour': np.random.choice([0, 1, 2, 3, 4, 5, 23], num_fraud),
        'day_of_week': np.random.randint(0, 7, num_fraud),
        'merchant_category': np.random.choice(['retail', 'food', 'gas', 'online'], num_fraud, p=[0.1, 0.1, 0.1, 0.7]),
        'distance_from_home': np.random.gamma(10, 20, num_fraud),
        'is_fraud': np.ones(num_fraud, dtype=int)
    }

    df_legitimate = pd.DataFrame(legitimate_transactions)
    df_fraud = pd.DataFrame(fraud_transactions)
    df = pd.concat([df_legitimate, df_fraud], ignore_index=True)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    merchant_cat_encoded = pd.get_dummies(df['merchant_category'], prefix='merchant')
    df = pd.concat([df.drop('merchant_category', axis=1), merchant_cat_encoded], axis=1)

    df.to_csv(output_data.path, index=False)
    print(f"Generated {num_samples} transactions ({num_fraud} fraud, {num_legitimate} legitimate)")
    print(f"Dataset shape: {df.shape}")
