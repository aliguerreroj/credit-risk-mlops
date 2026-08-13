import json
import statistics
import boto3
from datetime import datetime, timezone, timedelta

REGION = "us-east-1"
BUCKET = "ali-credit-risk-mlops-dev"
CAPTURE_PREFIX = "monitoring/data-capture/credit-risk-endpoint-dev/AllTraffic/"
BASELINE_STATS_KEY = "monitoring/baseline-output/statistics.json"
PIPELINE_NAME = "credit-risk-training-pipeline"
STD_DEV_THRESHOLD = 3
MAX_CAPTURE_AGE_HOURS = 2

s3 = boto3.client("s3", region_name=REGION)
sagemaker_client = boto3.client("sagemaker", region_name=REGION)


def load_baseline():
    obj = s3.get_object(Bucket=BUCKET, Key=BASELINE_STATS_KEY)
    stats = json.loads(obj["Body"].read())

    all_names = [feat["name"] for feat in stats["features"]]
    numeric_stats = {
        feat["name"]: feat["numerical_statistics"]
        for feat in stats["features"]
        if "numerical_statistics" in feat
    }
    return all_names, numeric_stats


def load_latest_capture():
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=CAPTURE_PREFIX)
    objects = response.get("Contents", [])
    if not objects:
        return None

    latest = max(objects, key=lambda obj: obj["LastModified"])

    age = datetime.now(timezone.utc) - latest["LastModified"]
    if age > timedelta(hours=MAX_CAPTURE_AGE_HOURS):
        print(f"El archivo más reciente tiene {age} de antigüedad — "
              f"supera el límite de {MAX_CAPTURE_AGE_HOURS}h. Se ignora.")
        return None

    obj = s3.get_object(Bucket=BUCKET, Key=latest["Key"])
    lines = obj["Body"].read().decode("utf-8").strip().split("\n")

    rows = []
    for line in lines:
        event = json.loads(line)
        raw_input = event["captureData"]["endpointInput"]["data"]
        values = [float(v) for v in raw_input.split(",")]
        rows.append(values)

    return rows


def check_drift(all_names, numeric_stats, rows):
    violations = []

    for col_idx, col_name in enumerate(all_names[: len(rows[0])]):
        if col_name not in numeric_stats:
            continue

        current_values = [row[col_idx] for row in rows]
        current_mean = statistics.mean(current_values)

        baseline_mean = numeric_stats[col_name]["mean"]
        baseline_std = numeric_stats[col_name]["std_dev"]

        if baseline_std == 0:
            continue

        z_score = abs(current_mean - baseline_mean) / baseline_std

        if z_score > STD_DEV_THRESHOLD:
            violations.append({"column": col_name, "z_score": round(z_score, 2)})

    return violations


def lambda_handler(event, context):
    all_names, numeric_stats = load_baseline()
    rows = load_latest_capture()

    if rows is None:
        print("No hay datos capturados todavía. Nada que analizar.")
        return {"status": "no_data", "drift_detected": False}

    violations = check_drift(all_names, numeric_stats, rows)

    if violations:
        print(f"DRIFT DETECTADO en {len(violations)} columnas: {violations}")
        response = sagemaker_client.start_pipeline_execution(
            PipelineName=PIPELINE_NAME
        )
        print(f"Pipeline de reentrenamiento disparado: {response['PipelineExecutionArn']}")
        return {
            "status": "drift_detected",
            "drift_detected": True,
            "violations": violations,
            "pipeline_execution_arn": response["PipelineExecutionArn"],
        }
    else:
        print("Sin drift detectado. No se dispara reentrenamiento.")
        return {"status": "ok", "drift_detected": False}

# if __name__ == "__main__":
#     result = lambda_handler({}, {})
#     print(result)