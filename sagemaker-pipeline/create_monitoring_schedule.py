import boto3
import sagemaker
from sagemaker.model_monitor import DefaultModelMonitor, CronExpressionGenerator
from sagemaker.model_monitor.dataset_format import DatasetFormat

region = "us-east-1"
role_arn = "arn:aws:iam::637992521859:role/credit-risk-sagemaker-role-dev"
bucket = "ali-credit-risk-mlops-dev"
endpoint_name = "credit-risk-endpoint-dev"

sagemaker_session = sagemaker.Session(boto3.Session(region_name=region))

my_monitor = DefaultModelMonitor(
    role=role_arn,
    instance_count=1,
    instance_type="ml.m5.xlarge",
    volume_size_in_gb=20,
    max_runtime_in_seconds=1800,
    sagemaker_session=sagemaker_session,
)

my_monitor.create_monitoring_schedule(
    monitor_schedule_name="credit-risk-monitor-schedule-dev",
    endpoint_input=endpoint_name,
    statistics=f"s3://{bucket}/monitoring/baseline-output/statistics.json",
    constraints=f"s3://{bucket}/monitoring/baseline-output/constraints.json",
    schedule_cron_expression=CronExpressionGenerator.hourly(),
    output_s3_uri=f"s3://{bucket}/monitoring/reports/",
)

print("Monitoring Schedule creado: credit-risk-monitor-schedule-dev")