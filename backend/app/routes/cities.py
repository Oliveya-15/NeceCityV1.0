from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import City
from app.routes.deps import get_city_or_404
from app.schemas import CityOut, CitySummaryOut
from app.services import city_service

router = APIRouter(prefix="/cities", tags=["cities"])


@router.get("", response_model=list[CityOut])
def list_cities(db: Session = Depends(get_db)):
    return city_service.list_cities(db)


@router.get("/{city_id}/summary", response_model=CitySummaryOut)
def city_summary(city: City = Depends(get_city_or_404), db: Session = Depends(get_db)):
    return city_service.get_city_summary(db, city)
