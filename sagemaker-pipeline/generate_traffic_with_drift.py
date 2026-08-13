import json
import time
import boto3
import pandas as pd

region = "us-east-1"
bucket = "ali-credit-risk-mlops-dev"
endpoint_name = "credit-risk-endpoint-dev"
baseline_stats_key = "monitoring/baseline-output/statistics.json"

N_SAMPLES = 15
DRIFT_MULTIPLIER = 5
COLUMNS_TO_DRIFT = ["AMT_INCOME_TOTAL", "AMT_CREDIT"]

s3 = boto3.client("s3", region_name=region)
sagemaker_runtime = boto3.client("sagemaker-runtime", region_name=region)

# --- Paso 1: obtener el orden real de columnas desde el baseline ---
baseline_obj = s3.get_object(Bucket=bucket, Key=baseline_stats_key)
baseline_stats = json.loads(baseline_obj["Body"].read())
all_feature_names = [feat["name"] for feat in baseline_stats["features"]]

# --- Paso 2: confirmar que las columnas objetivo existen, y ubicar su posición real ---
drift_indices = {}
for col_name in COLUMNS_TO_DRIFT:
    if col_name not in all_feature_names:
        raise ValueError(f"La columna '{col_name}' no existe en el baseline.")
    drift_indices[col_name] = all_feature_names.index(col_name)

print("Columnas a modificar y su posición real:")
for name, idx in drift_indices.items():
    print(f"  {name} -> índice {idx}")

# --- Paso 3: cargar datos de prueba y aplicar el drift por posición confirmada ---
test_df = pd.read_csv("test.csv", header=None)
samples = test_df.iloc[:N_SAMPLES, 1:].copy()
samples.columns = all_feature_names[: samples.shape[1]]

for col_name in COLUMNS_TO_DRIFT:
    samples[col_name] = samples[col_name] * DRIFT_MULTIPLIER

# --- Paso 4: enviar las predicciones ---
print(f"\nEnviando {N_SAMPLES} predicciones CON DRIFT SIMULADO al Endpoint...")

for i in range(N_SAMPLES):
    row = samples.iloc[i]
    csv_payload = ",".join(str(v) for v in row)

    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType="text/csv",
        Body=csv_payload,
    )
    probability = float(response["Body"].read().decode())
    print(f"Fila {i}: probabilidad = {probability:.4f}")

    time.sleep(0.5)

print("Tráfico con drift simulado generado.")