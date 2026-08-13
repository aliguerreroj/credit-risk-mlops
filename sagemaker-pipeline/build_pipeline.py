import sagemaker
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.steps import ProcessingStep, TrainingStep
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.conditions import ConditionGreaterThanOrEqualTo
from sagemaker.workflow.functions import JsonGet
from sagemaker.workflow.model_step import ModelStep
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.processing import ProcessingInput, ProcessingOutput
from sagemaker.estimator import Estimator
from sagemaker.inputs import TrainingInput
from sagemaker.model import Model
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.pipeline_context import PipelineSession
from sagemaker.processing import ScriptProcessor
import boto3

# --- Configuración base ---
region = "us-east-1"
bucket = "ali-credit-risk-mlops-dev"
role_arn = "arn:aws:iam::637992521859:role/credit-risk-sagemaker-role-dev"

sagemaker_session = PipelineSession(boto_session=boto3.Session(region_name=region))


# --- Paso 1: Preprocesamiento (instancia económica, cuota confirmada) ---
sklearn_processor = SKLearnProcessor(
    framework_version="1.2-1",
    role=role_arn,
    instance_type="ml.t3.medium",
    instance_count=1,
    sagemaker_session=sagemaker_session,
    base_job_name="credit-risk-preprocess"
)

step_preprocess = ProcessingStep(
    name="PreprocessData",
    processor=sklearn_processor,
    inputs=[
        ProcessingInput(
            source=f"s3://{bucket}/processed/application_bureau_merged/",
            destination="/opt/ml/processing/input"
        )
    ],
    outputs=[
        ProcessingOutput(output_name="train", source="/opt/ml/processing/train"),
        ProcessingOutput(output_name="test", source="/opt/ml/processing/test")
    ],
    code="scripts/preprocess.py"
)


# --- Paso 2: Entrenamiento (dentro de las 50h gratis/mes de training) ---
xgboost_image_uri = sagemaker.image_uris.retrieve(
    framework="xgboost",
    region=region,
    version="1.7-1"
)

xgb_estimator = Estimator(
    image_uri=xgboost_image_uri,
    role=role_arn,
    instance_type="ml.m5.xlarge",
    instance_count=1,
    output_path=f"s3://{bucket}/models/",
    sagemaker_session=sagemaker_session,
    base_job_name="credit-risk-xgboost"
)

xgb_estimator.set_hyperparameters(
    max_depth=5,
    eta=0.05,
    objective="binary:logistic",
    num_round=200,
    scale_pos_weight=11.39,
    eval_metric="auc"
)

step_train = TrainingStep(
    name="TrainModel",
    estimator=xgb_estimator,
    inputs={
        "train": TrainingInput(
            s3_data=step_preprocess.properties.ProcessingOutputConfig.Outputs["train"].S3Output.S3Uri,
            content_type="text/csv"
        )
    }
)

# --- Paso 3: Evaluación (instancia económica, cuota confirmada) ---
script_processor = ScriptProcessor(
    image_uri=xgboost_image_uri,
    command=["python3"],
    role=role_arn,
    instance_type="ml.t3.medium",
    instance_count=1,
    sagemaker_session=sagemaker_session,
    base_job_name="credit-risk-evaluate"
)

evaluation_report = PropertyFile(
    name="EvaluationReport",
    output_name="evaluation",
    path="evaluation.json"
)

step_evaluate = ProcessingStep(
    name="EvaluateModel",
    processor=script_processor,
    inputs=[
        ProcessingInput(
            source=step_train.properties.ModelArtifacts.S3ModelArtifacts,
            destination="/opt/ml/processing/model"
        ),
        ProcessingInput(
            source=step_preprocess.properties.ProcessingOutputConfig.Outputs["test"].S3Output.S3Uri,
            destination="/opt/ml/processing/test"
        )
    ],
    outputs=[
        ProcessingOutput(output_name="evaluation", source="/opt/ml/processing/evaluation")
    ],
    code="scripts/evaluate.py",
    property_files=[evaluation_report]
)

model = Model(
    image_uri=xgboost_image_uri,
    model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
    role=role_arn,
    sagemaker_session=sagemaker_session
)

step_register = ModelStep(
    name="RegisterModel",
    step_args=model.register(
        content_types=["text/csv"],
        response_types=["text/csv"],
        inference_instances=["ml.m5.large"],
        transform_instances=["ml.m5.large"],
        model_package_group_name="credit-risk-model-group",
        approval_status="PendingManualApproval"
    )
)

step_condition = ConditionStep(
    name="CheckAUCThreshold",
    conditions=[
        ConditionGreaterThanOrEqualTo(
            left=JsonGet(
                step_name=step_evaluate.name,
                property_file=evaluation_report,
                json_path="binary_classification_metrics.auc.value"
            ),
            right=0.70
        )
    ],
    if_steps=[step_register],
    else_steps=[]
)


pipeline = Pipeline(
    name="credit-risk-training-pipeline",
    steps=[step_preprocess, step_train, step_evaluate, step_condition],
    sagemaker_session=sagemaker_session
)

pipeline.upsert(role_arn=role_arn)

print("Pipeline creado/actualizado exitosamente.")
print(f"Nombre del pipeline: {pipeline.name}")

execution = pipeline.start()
print(f"Ejecución iniciada: {execution.arn}")