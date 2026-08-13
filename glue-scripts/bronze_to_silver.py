import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, when, count, max as spark_max, mean, sum as spark_sum

# --- Setup estándar de Glue ---
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'S3_BUCKET'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

bucket = args['S3_BUCKET']

# --- Cargar datos crudos desde Bronze (raw/) ---
df = spark.read.csv(f"s3://{bucket}/raw/application_train.csv", header=True, inferSchema=True)
bureau = spark.read.csv(f"s3://{bucket}/raw/bureau.csv", header=True, inferSchema=True)

# --- Limpieza de application_train: eliminar columnas sin señal predictiva ---
cols_sin_senal = [
    'OWN_CAR_AGE', 'APARTMENTS_AVG', 'BASEMENTAREA_AVG', 'YEARS_BUILD_AVG',
    'COMMONAREA_AVG', 'ELEVATORS_AVG', 'ENTRANCES_AVG', 'FLOORSMIN_AVG',
    'LANDAREA_AVG', 'LIVINGAPARTMENTS_AVG', 'LIVINGAREA_AVG',
    'NONLIVINGAPARTMENTS_AVG', 'NONLIVINGAREA_AVG', 'APARTMENTS_MODE',
    'BASEMENTAREA_MODE', 'YEARS_BUILD_MODE', 'COMMONAREA_MODE',
    'ELEVATORS_MODE', 'ENTRANCES_MODE', 'FLOORSMIN_MODE', 'LANDAREA_MODE',
    'LIVINGAPARTMENTS_MODE', 'LIVINGAREA_MODE', 'NONLIVINGAPARTMENTS_MODE',
    'NONLIVINGAREA_MODE', 'APARTMENTS_MEDI', 'BASEMENTAREA_MEDI',
    'YEARS_BUILD_MEDI', 'COMMONAREA_MEDI', 'ELEVATORS_MEDI',
    'ENTRANCES_MEDI', 'FLOORSMIN_MEDI', 'LANDAREA_MEDI',
    'LIVINGAPARTMENTS_MEDI', 'LIVINGAREA_MEDI', 'NONLIVINGAPARTMENTS_MEDI',
    'NONLIVINGAREA_MEDI', 'FONDKAPREMONT_MODE',
    'FLOORSMAX_AVG', 'FLOORSMAX_MODE', 'FLOORSMAX_MEDI',
    'YEARS_BEGINEXPLUATATION_AVG', 'YEARS_BEGINEXPLUATATION_MODE',
    'YEARS_BEGINEXPLUATATION_MEDI', 'TOTALAREA_MODE',
    'AMT_REQ_CREDIT_BUREAU_HOUR', 'AMT_REQ_CREDIT_BUREAU_DAY',
    'AMT_REQ_CREDIT_BUREAU_WEEK', 'AMT_REQ_CREDIT_BUREAU_MON',
    'AMT_REQ_CREDIT_BUREAU_QRT', 'AMT_REQ_CREDIT_BUREAU_YEAR'
]

df_clean = df.drop(*cols_sin_senal)

# --- Imputación de columnas conservadas ---
mediana_ext1 = df_clean.approxQuantile("EXT_SOURCE_1", [0.5], 0.01)[0]
mediana_ext3 = df_clean.approxQuantile("EXT_SOURCE_3", [0.5], 0.01)[0]

df_clean = df_clean.withColumn(
    "EXT_SOURCE_1_MISSING",
    when(col("EXT_SOURCE_1").isNull(), 1).otherwise(0)
)
df_clean = df_clean.withColumn(
    "EXT_SOURCE_3_MISSING",
    when(col("EXT_SOURCE_3").isNull(), 1).otherwise(0)
)

df_clean = df_clean.fillna({
    "EXT_SOURCE_1": mediana_ext1,
    "EXT_SOURCE_3": mediana_ext3,
    "HOUSETYPE_MODE": "Desconocido",
    "WALLSMATERIAL_MODE": "Desconocido",
    "EMERGENCYSTATE_MODE": "Desconocido",
    "OCCUPATION_TYPE": "Desconocido",
    "NAME_TYPE_SUITE": "Unaccompanied"
})

# --- Escribir application limpio en Silver ---
df_clean.write.mode("overwrite").parquet(f"s3://{bucket}/silver/application_clean/")

# --- Agregación de bureau.csv a nivel cliente ---
bureau_agg = bureau.groupBy("SK_ID_CURR").agg(
    count("SK_ID_BUREAU").alias("BUREAU_CREDIT_COUNT"),
    spark_max("CREDIT_DAY_OVERDUE").alias("BUREAU_DAYS_OVERDUE_MAX"),
    mean("CREDIT_DAY_OVERDUE").alias("BUREAU_DAYS_OVERDUE_MEAN"),
    spark_sum("AMT_CREDIT_SUM").alias("BUREAU_CREDIT_SUM_TOTAL"),
    spark_sum("AMT_CREDIT_SUM_DEBT").alias("BUREAU_CREDIT_SUM_DEBT"),
    spark_sum("AMT_CREDIT_SUM_OVERDUE").alias("BUREAU_CREDIT_SUM_OVERDUE"),
    spark_sum("CNT_CREDIT_PROLONG").alias("BUREAU_CREDIT_PROLONG_SUM")
)

bureau_active = bureau.filter(col("CREDIT_ACTIVE") == "Active") \
    .groupBy("SK_ID_CURR") \
    .agg(count("SK_ID_BUREAU").alias("BUREAU_ACTIVE_COUNT"))

bureau_agg = bureau_agg.join(bureau_active, on="SK_ID_CURR", how="left")
bureau_agg = bureau_agg.fillna({"BUREAU_ACTIVE_COUNT": 0})

# --- Escribir bureau agregado en Silver ---
bureau_agg.write.mode("overwrite").parquet(f"s3://{bucket}/silver/bureau_agg/")

job.commit()