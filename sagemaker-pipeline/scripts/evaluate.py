import json
import os
import tarfile
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score, precision_score, recall_score

# --- Rutas que SageMaker usa por convención en un Processing Job de evaluación ---
model_path = "/opt/ml/processing/model"
test_path = "/opt/ml/processing/test"
output_path = "/opt/ml/processing/evaluation"

# --- Paso 1: descomprimir el modelo entrenado ---
# SageMaker entrega el modelo entrenado como un archivo model.tar.gz
model_tar_path = os.path.join(model_path, "model.tar.gz")
with tarfile.open(model_tar_path, "r:gz") as tar:
    tar.extractall(path=model_path)

# --- Paso 2: cargar el modelo con la librería nativa de xgboost ---
model = xgb.Booster()
model.load_model(os.path.join(model_path, "xgboost-model"))

# --- Paso 3: cargar el test set (mismo formato que escribió preprocess.py) ---
test_df = pd.read_csv(os.path.join(test_path, "test.csv"), header=None)

y_test = test_df.iloc[:, 0]        # primera columna = TARGET
X_test = test_df.iloc[:, 1:]       # el resto = features

# --- Paso 4: predecir sobre el test set ---
dtest = xgb.DMatrix(X_test)
y_pred_proba = model.predict(dtest)
y_pred = (y_pred_proba >= 0.5).astype(int)

# --- Paso 5: calcular métricas (mismas que en el notebook) ---
auc = roc_auc_score(y_test, y_pred_proba)
recall = recall_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)

print(f"AUC-ROC: {auc:.4f}")
print(f"Recall: {recall:.4f}")
print(f"Precision: {precision:.4f}")

# --- Paso 6: guardar métricas en el formato que SageMaker Pipelines espera ---
evaluation_report = {
    "binary_classification_metrics": {
        "auc": {"value": auc, "standard_deviation": "NaN"},
        "recall": {"value": recall, "standard_deviation": "NaN"},
        "precision": {"value": precision, "standard_deviation": "NaN"}
    }
}

os.makedirs(output_path, exist_ok=True)
with open(os.path.join(output_path, "evaluation.json"), "w") as f:
    json.dump(evaluation_report, f)

print("Evaluación completada.")