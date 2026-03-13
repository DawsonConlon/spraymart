from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.db.session import get_db
from app.models.field import Field, Farm
from app.schemas.field import FieldCreate, FieldResponse

router = APIRouter()


@router.post("/", response_model=FieldResponse, status_code=201)
async def create_field(payload: FieldCreate, db: AsyncSession = Depends(get_db)):
    field = Field(**payload.model_dump())
    db.add(field)
    await db.commit()
    await db.refresh(field)
    return field


@router.get("/{field_id}", response_model=FieldResponse)
async def get_field(field_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Field).where(Field.id == field_id))
    field = result.scalar_one_or_none()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    return field


@router.get("/farm/{farm_id}", response_model=list[FieldResponse])
async def list_fields(farm_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Field).where(Field.farm_id == farm_id))
    return result.scalars().all()
