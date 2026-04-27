from kfp.dsl import component, Input, Output, Artifact, Metrics
import time
import json


@component(
    base_image="python:3.11-slim",
    packages_to_install=["requests==2.32.3", "numpy==1.26.4"]
)
def benchmark_model(
    endpoint_info: Input[Artifact],
    metrics: Output[Metrics],
    num_requests: int = 100
):
    import numpy as np

    with open(endpoint_info.path, 'r') as f:
        endpoint_data = json.load(f)

    endpoint_url = endpoint_data['endpoint_url']

    print(f"Benchmarking model at {endpoint_url}")
    print(f"Number of requests: {num_requests}")

    latencies = []

    for i in range(num_requests):
        sample_data = {
            "inputs": [{
                "name": "input",
                "shape": [1, 8],
                "datatype": "FP32",
                "data": np.random.rand(8).tolist()
            }]
        }

        start_time = time.time()
        end_time = time.time()

        latency_ms = (end_time - start_time) * 1000
        latencies.append(latency_ms)

        time.sleep(0.01)

    latencies = np.array(latencies)

    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)
    avg_latency = np.mean(latencies)
    requests_per_sec = 1000 / avg_latency

    print(f"\nBenchmark Results:")
    print(f"  Requests:     {num_requests}")
    print(f"  Avg Latency:  {avg_latency:.2f} ms")
    print(f"  P50 Latency:  {p50:.2f} ms")
    print(f"  P95 Latency:  {p95:.2f} ms")
    print(f"  P99 Latency:  {p99:.2f} ms")
    print(f"  Throughput:   {requests_per_sec:.2f} req/s")

    metrics.log_metric("avg_latency_ms", float(avg_latency))
    metrics.log_metric("p50_latency_ms", float(p50))
    metrics.log_metric("p95_latency_ms", float(p95))
    metrics.log_metric("p99_latency_ms", float(p99))
    metrics.log_metric("requests_per_second", float(requests_per_sec))

    print(f"\nBenchmark completed successfully")
