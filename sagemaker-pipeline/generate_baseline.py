import pandas as pd
import boto3
import sagemaker
from sagemaker.model_monitor import DefaultModelMonitor
from sagemaker.model_monitor.dataset_format import DatasetFormat

region = "us-east-1"
bucket = "ali-credit-risk-mlops-dev"
role_arn = "arn:aws:iam::637992521859:role/credit-risk-sagemaker-role-dev"

# --- Paso 1: reconstruir el dataset CON nombres de columna reales ---
# (mismo proceso exacto que scripts/preprocess.py, pero conservando headers)
s3 = boto3.client("s3")
response = s3.list_objects_v2(Bucket=bucket, Prefix="processed/application_bureau_merged/")
parquet_keys = [obj["Key"] for obj in response["Contents"] if obj["Key"].endswith(".parquet")]

dfs = [pd.read_parquet(f"s3://{bucket}/{key}") for key in parquet_keys]
df = pd.concat(dfs, ignore_index=True)

cols_categoricas = df.select_dtypes(include=["object"]).columns.tolist()
df_encoded = pd.get_dummies(df, columns=cols_categoricas, drop_first=True)

X = df_encoded.drop(columns=["TARGET", "SK_ID_CURR"])

# --- Paso 2: guardar localmente CON header, subir a S3 ---
baseline_local_path = "baseline_features.csv"
X.to_csv(baseline_local_path, index=False, header=True)

baseline_s3_uri = f"s3://{bucket}/monitoring/baseline-data/baseline_features.csv"
s3.upload_file(baseline_local_path, bucket, "monitoring/baseline-data/baseline_features.csv")
print(f"Baseline con headers subido a: {baseline_s3_uri}")

# --- Paso 3: correr el job de Model Monitor sobre ese baseline ---
sagemaker_session = sagemaker.Session(boto3.Session(region_name=region))

my_monitor = DefaultModelMonitor(
    role=role_arn,
    instance_count=1,
    instance_type="ml.m5.xlarge",
    volume_size_in_gb=20,
    max_runtime_in_seconds=1800,
    sagemaker_session=sagemaker_session,
)

my_monitor.suggest_baseline(
    baseline_dataset=baseline_s3_uri,
    dataset_format=DatasetFormat.csv(header=True),
    output_s3_uri=f"s3://{bucket}/monitoring/baseline-output/",
)

print("Job de baseline lanzado. Statistics y constraints se guardarán en:")
print(f"s3://{bucket}/monitoring/baseline-output/")