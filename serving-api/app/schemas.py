from pydantic import BaseModel, Field
from typing import List


class PredictionRequest(BaseModel):
    """
    Features del solicitante, en el mismo orden y formato
    que espera el modelo XGBoost (CSV sin header, TARGET excluido).
    """
    features: List[float] = Field(
        ...,
        description="Vector de features en el orden exacto del training set",
        min_length=1,
    )


class PredictionResponse(BaseModel):
    probability_of_default: float
    risk_level: str  # "low" | "medium" | "high", derivado del threshold


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool