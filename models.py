from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MealEntry(BaseModel):
    # Identification
    meal_name: str
    meal_type: str  # Breakfast, Lunch, etc.
    category: str  # catering, home, restaurant
    source: str  # Brokul, Homemade

    # Nutrition per box or per 100g
    kcal_base: float
    protein_base: float
    fat_total_base: float
    fat_saturated_base: float
    carbs_total_base: float
    sugars_base: float
    salt_base: float

    # Weight logic
    is_weighted: bool = False
    weight_consumed_g: Optional[float] = None
    reference_size_g: float = 100.0

    # Timestamp
    log_time: Optional[datetime] = None


class WeightEntry(BaseModel):
    weight: Optional[float] = None
    waist: Optional[float] = None   # cm
    chest: Optional[float] = None   # cm
    log_time: Optional[datetime] = None

    def model_post_init(self, __context):
        if self.weight is None and self.waist is None and self.chest is None:
            raise ValueError("At least one measurement (weight, waist, or chest) must be provided")