import os
import tarfile
import boto3
import xgboost as xgb

MODEL_S3_BUCKET = os.environ["MODEL_S3_BUCKET"]
MODEL_S3_KEY = os.environ["MODEL_S3_KEY"]
LOCAL_MODEL_DIR = "/tmp/model"
LOCAL_MODEL_PATH = f"{LOCAL_MODEL_DIR}/xgboost-model"


def download_and_load_model() -> xgb.Booster:
    os.makedirs(LOCAL_MODEL_DIR, exist_ok=True)
    local_tar_path = f"{LOCAL_MODEL_DIR}/model.tar.gz"

    s3 = boto3.client("s3")
    s3.download_file(MODEL_S3_BUCKET, MODEL_S3_KEY, local_tar_path)

    with tarfile.open(local_tar_path, "r:gz") as tar:
        tar.extractall(path=LOCAL_MODEL_DIR)

    booster = xgb.Booster()
    booster.load_model(LOCAL_MODEL_PATH)
    return booster