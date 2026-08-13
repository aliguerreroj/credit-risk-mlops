import sagemaker
import boto3
from sagemaker import ModelPackage
from sagemaker.model_monitor import DataCaptureConfig

region = "us-east-1"
role_arn = "arn:aws:iam::637992521859:role/credit-risk-sagemaker-role-dev"
model_package_arn = "arn:aws:sagemaker:us-east-1:637992521859:model-package/credit-risk-model-group/1"
bucket = "ali-credit-risk-mlops-dev"

sagemaker_session = sagemaker.Session(boto3.Session(region_name=region))

model = ModelPackage(
    role=role_arn,
    model_package_arn=model_package_arn,
    sagemaker_session=sagemaker_session
)

data_capture_config = DataCaptureConfig(
    enable_capture=True,
    sampling_percentage=100,
    destination_s3_uri=f"s3://{bucket}/monitoring/data-capture"
)

endpoint_name = "credit-risk-endpoint-dev"

predictor = model.deploy(
    initial_instance_count=1,
    instance_type="ml.m5.large",
    endpoint_name=endpoint_name,
    data_capture_config=data_capture_config
)

print(f"Endpoint desplegado con Data Capture activado: {endpoint_name}")