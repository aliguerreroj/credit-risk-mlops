import time
import boto3
import pandas as pd
import requests
import json

# --- Configuración ---
SAGEMAKER_ENDPOINT_NAME = "credit-risk-endpoint-dev"
API_GATEWAY_URL = "https://ifkxzvt1wh.execute-api.us-east-1.amazonaws.com/predict"
N_SAMPLES = 10

# --- Cargar datos de prueba ---
test_df = pd.read_csv("../sagemaker-pipeline/test.csv", header=None)
samples = test_df.iloc[:N_SAMPLES, 1:]

# --- Camino A: SageMaker Endpoint ---
sagemaker_runtime = boto3.client("sagemaker-runtime")

def call_sagemaker(features_row):
    csv_payload = ",".join(str(v) for v in features_row)
    start = time.perf_counter()
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT_NAME,
        ContentType="text/csv",
        Body=csv_payload,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000
    probability = float(response["Body"].read().decode())
    return probability, elapsed_ms

# --- Camino B: API Gateway → ECS Fargate ---
def call_ecs_api(features_row):
    payload = {"features": features_row.tolist()}
    start = time.perf_counter()
    response = requests.post(API_GATEWAY_URL, json=payload)
    elapsed_ms = (time.perf_counter() - start) * 1000
    probability = response.json()["probability_of_default"]
    return probability, elapsed_ms

# --- Correr la comparación ---
results = []
for i in range(N_SAMPLES):
    row = samples.iloc[i]

    prob_a, latency_a = call_sagemaker(row)
    prob_b, latency_b = call_ecs_api(row)

    results.append({
        "row": i,
        "sagemaker_probability": round(prob_a, 4),
        "ecs_probability": round(prob_b, 4),
        "match": abs(prob_a - prob_b) < 0.0001,
        "sagemaker_latency_ms": round(latency_a, 1),
        "ecs_latency_ms": round(latency_b, 1),
    })

# --- Resumen ---
results_df = pd.DataFrame(results)
print(results_df.to_string(index=False))

print("\n--- Resumen ---")
print(f"Coincidencias exactas: {results_df['match'].sum()}/{N_SAMPLES}")
print(f"Latencia promedio SageMaker: {results_df['sagemaker_latency_ms'].mean():.1f} ms")
print(f"Latencia promedio ECS/API Gateway: {results_df['ecs_latency_ms'].mean():.1f} ms")