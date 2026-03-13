from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from app.services.spray_scorer import SprayDecision
from app.services.gdd_engine import PlantStage


class RecommendationResponse(BaseModel):
    field_id: UUID
    field_name: str
    decision: SprayDecision
    summary: str
    overall_score: float
    gdd_accumulated: float
    estimated_stage: PlantStage
    stage_confidence: float
    condition_checks: list[dict]

    model_config = {"from_attributes": True}
