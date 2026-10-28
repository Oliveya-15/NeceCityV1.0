from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import City
from app.services.city_service import get_city


def get_city_or_404(city_id: int, db: Session = Depends(get_db)) -> City:
    city = get_city(db, city_id)
    if city is None:
        raise HTTPException(status_code=404, detail=f"City {city_id} not found.")
    return city
