import pandas as pd
import os
import glob
from sklearn.model_selection import train_test_split

# --- Rutas que SageMaker usa por convención ---
input_path = "/opt/ml/processing/input"
output_train_path = "/opt/ml/processing/train"
output_test_path = "/opt/ml/processing/test"

# --- Cargar los archivos Parquet (pueden ser varios, por las particiones de Spark) ---
parquet_files = glob.glob(os.path.join(input_path, "*.parquet"))
df = pd.concat([pd.read_parquet(f) for f in parquet_files], ignore_index=True)

print(f"Datos cargados: {df.shape}")

# --- Encoding categórico ---
cols_categoricas = df.select_dtypes(include=['object']).columns.tolist()
df_encoded = pd.get_dummies(df, columns=cols_categoricas, drop_first=True)

print(f"Después de encoding: {df_encoded.shape}")

# --- Separar features y target ---
X = df_encoded.drop(columns=['TARGET', 'SK_ID_CURR'])
y = df_encoded['TARGET']

# --- Train/test split estratificado ---
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# --- Reconstruir dataframes con TARGET como PRIMERA columna ---
# (requisito del algoritmo XGBoost integrado de SageMaker)
train_df = pd.concat([y_train.reset_index(drop=True), X_train.reset_index(drop=True)], axis=1)
test_df = pd.concat([y_test.reset_index(drop=True), X_test.reset_index(drop=True)], axis=1)

# --- Guardar resultados (sin header, sin índice) ---
os.makedirs(output_train_path, exist_ok=True)
os.makedirs(output_test_path, exist_ok=True)

train_df.to_csv(os.path.join(output_train_path, "train.csv"), index=False, header=False)
test_df.to_csv(os.path.join(output_test_path, "test.csv"), index=False, header=False)

print(f"Train: {train_df.shape}, Test: {test_df.shape}")
print("Preprocesamiento completado.")