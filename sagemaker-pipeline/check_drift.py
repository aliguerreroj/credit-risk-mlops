import json
import boto3
import pandas as pd

region = "us-east-1"
bucket = "ali-credit-risk-mlops-dev"
capture_prefix = "monitoring/data-capture/credit-risk-endpoint-dev/AllTraffic/"
baseline_stats_key = "monitoring/baseline-output/statistics.json"
STD_DEV_THRESHOLD = 3  # cuántas desviaciones estándar cuentan como "drift"

s3 = boto3.client("s3", region_name=region)

# --- Paso 1: descargar y parsear el baseline ---
baseline_obj = s3.get_object(Bucket=bucket, Key=baseline_stats_key)
baseline_stats = json.loads(baseline_obj["Body"].read())

all_feature_names = [feat["name"] for feat in baseline_stats["features"]]

baseline_features = {}
skipped = []

for feat in baseline_stats["features"]:
    if "numerical_statistics" in feat:
        baseline_features[feat["name"]] = feat["numerical_statistics"]
    else:
        skipped.append((feat["name"], feat.get("inferred_type", "desconocido")))

print(f"Columnas totales en el baseline: {len(all_feature_names)}")
print(f"Columnas numéricas usables: {len(baseline_features)}")
if skipped:
    print(f"Columnas omitidas (sin numerical_statistics): {len(skipped)}")

# --- Paso 2: listar los archivos .jsonl capturados y quedarnos solo con el más reciente ---
response = s3.list_objects_v2(Bucket=bucket, Prefix=capture_prefix)
all_capture_objects = [obj for obj in response.get("Contents", []) if obj["Key"].endswith(".jsonl")]

latest_object = max(all_capture_objects, key=lambda obj: obj["LastModified"])
capture_keys = [latest_object["Key"]]

print(f"Analizando el archivo más reciente: {latest_object['Key']}")
print(f"Archivos de captura encontrados: {len(capture_keys)}")

# --- Paso 3: leer y parsear las predicciones capturadas ---
captured_rows = []
for key in capture_keys:
    obj = s3.get_object(Bucket=bucket, Key=key)
    lines = obj["Body"].read().decode("utf-8").strip().split("\n")
    for line in lines:
        event = json.loads(line)
        raw_input = event["captureData"]["endpointInput"]["data"]
        values = [float(v) for v in raw_input.split(",")]
        captured_rows.append(values)

print(f"Predicciones capturadas: {len(captured_rows)}")

# --- Paso 4: calcular estadísticas actuales por columna ---
captured_df = pd.DataFrame(captured_rows)
captured_df.columns = all_feature_names[: captured_df.shape[1]]

# --- Paso 5: comparar contra el baseline (solo columnas numéricas usables) ---
print("\n--- Reporte de Drift ---")
violations = 0

for col in baseline_features.keys():
    current_mean = captured_df[col].mean()
    baseline_mean = baseline_features[col]["mean"]
    baseline_std = baseline_features[col]["std_dev"]

    if baseline_std == 0:
        continue

    z_score = abs(current_mean - baseline_mean) / baseline_std

    if z_score > STD_DEV_THRESHOLD:
        violations += 1
        print(f"[DRIFT] {col}: baseline_mean={baseline_mean:.4f}, "
              f"current_mean={current_mean:.4f}, z_score={z_score:.2f}")

print(f"\nTotal de columnas con posible drift: {violations}/{len(captured_df.columns)}")    