import time
import boto3
import pandas as pd

region = "us-east-1"
endpoint_name = "credit-risk-endpoint-dev"
N_SAMPLES = 15

sagemaker_runtime = boto3.client("sagemaker-runtime", region_name=region)

test_df = pd.read_csv("test.csv", header=None)
samples = test_df.iloc[:N_SAMPLES, 1:]

print(f"Enviando {N_SAMPLES} predicciones al Endpoint...")

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

print("Tráfico generado. Data Capture debería tener estas 15 predicciones registradas.")