import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, when

# --- Setup estándar de Glue ---
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'S3_BUCKET'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

bucket = args['S3_BUCKET']

# --- Cargar datos desde Silver (ya limpios, ya agregados) ---
df_clean = spark.read.parquet(f"s3://{bucket}/silver/application_clean/")
bureau_agg = spark.read.parquet(f"s3://{bucket}/silver/bureau_agg/")

# --- Unir application + bureau ---
df_merged = df_clean.join(bureau_agg, on="SK_ID_CURR", how="left")

df_merged = df_merged.withColumn(
    "BUREAU_HISTORY_MISSING",
    when(col("BUREAU_CREDIT_COUNT").isNull(), 1).otherwise(0)
)

cols_bureau = [
    "BUREAU_CREDIT_COUNT", "BUREAU_DAYS_OVERDUE_MAX", "BUREAU_DAYS_OVERDUE_MEAN",
    "BUREAU_CREDIT_SUM_TOTAL", "BUREAU_CREDIT_SUM_DEBT",
    "BUREAU_CREDIT_SUM_OVERDUE", "BUREAU_CREDIT_PROLONG_SUM", "BUREAU_ACTIVE_COUNT"
]
df_merged = df_merged.fillna({c: 0 for c in cols_bureau})

# --- Escribir resultado final en Gold ---
df_merged.write.mode("overwrite").parquet(f"s3://{bucket}/processed/application_bureau_merged/")

job.commit()