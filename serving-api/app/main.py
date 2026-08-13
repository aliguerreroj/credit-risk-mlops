from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import xgboost as xgb

from app.schemas import PredictionRequest, PredictionResponse, HealthResponse
from app.model_loader import download_and_load_model

DECISION_THRESHOLD = 0.5
model_state = {"model": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_state["model"] = download_and_load_model()
    yield
    model_state.clear()


app = FastAPI(title="Credit Risk Scoring API", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        model_loaded=model_state["model"] is not None,
    )


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    model = model_state["model"]
    if model is None:
        raise HTTPException(status_code=503, detail="Modelo no disponible aún")

    dmatrix = xgb.DMatrix([request.features])
    probability = float(model.predict(dmatrix)[0])

    risk_level = "high" if probability >= DECISION_THRESHOLD else "low"

    return PredictionResponse(
        probability_of_default=probability,
        risk_level=risk_level,
    )