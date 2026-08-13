import boto3
import pandas as pd

# --- Configuración ---
region = "us-east-1"
endpoint_name = "credit-risk-endpoint-dev"

runtime = boto3.client("sagemaker-runtime", region_name=region)

# --- Tomamos una fila de ejemplo de tu test set (descargado antes) ---
# Recuerda: el formato es TARGET, feature1, feature2, ... (sin header)
# Para la predicción, mandamos SOLO las features (sin la columna TARGET)

test_df = pd.read_csv("test.csv", header=None)  # ajusta la ruta si es necesario
sample = test_df.iloc[0, 1:]  # primera fila, todas las columnas EXCEPTO la primera (TARGET)

payload = ",".join(map(str, sample.values))

# --- Invocar el endpoint ---
response = runtime.invoke_endpoint(
    EndpointName=endpoint_name,
    ContentType="text/csv",
    Body=payload
)

result = response["Body"].read().decode("utf-8")
print(f"Probabilidad de default predicha: {result}")
print(f"TARGET real de esta fila: {test_df.iloc[0, 0]}")