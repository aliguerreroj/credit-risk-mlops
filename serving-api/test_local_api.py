import json
import pandas as pd
import requests

test_df = pd.read_csv("../sagemaker-pipeline/test.csv", header=None)
sample = test_df.iloc[0, 1:]

payload = {"features": sample.tolist()}

response = requests.post("http://localhost:8000/predict", json=payload)

print("Status code:", response.status_code)
print("Respuesta:", response.json())
print("TARGET real de esta fila:", test_df.iloc[0, 0])