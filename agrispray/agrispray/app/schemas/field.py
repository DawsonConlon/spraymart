from pydantic import BaseModel
from uuid import UUID
from datetime import date
from typing import Optional
from app.models.field import CropType


class FieldCreate(BaseModel):
    farm_id: UUID
    name: str
    lsd: str
    crop_type: CropType
    plant_date: date
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    previous_crop_type: Optional[CropType] = None
    last_spray_date: Optional[date] = None


class FieldResponse(FieldCreate):
    id: UUID
    model_config = {"from_attributes": True}
