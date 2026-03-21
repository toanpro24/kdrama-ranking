from pydantic import BaseModel, Field
from typing import Optional


class Drama(BaseModel):
    title: str
    year: int
    role: str = ""
    poster: Optional[str] = None


class ActressCreate(BaseModel):
    name: str
    known: str = "—"
    genre: str = "Romance"
    year: int = 2024
    image: Optional[str] = None
    birthDate: Optional[str] = None
    birthPlace: Optional[str] = None
    agency: Optional[str] = None
    dramas: list[Drama] = []
    awards: list[str] = []
    gallery: list[str] = []


class ActressResponse(BaseModel):
    id: str = Field(alias="_id")
    name: str
    known: str
    genre: str
    year: int
    tier: Optional[str] = None
    image: Optional[str] = None
    birthDate: Optional[str] = None
    birthPlace: Optional[str] = None
    agency: Optional[str] = None
    dramas: list[Drama] = []
    awards: list[str] = []
    gallery: list[str] = []

    class Config:
        populate_by_name = True


class TierUpdate(BaseModel):
    tier: Optional[str] = None  # "splus", "s", "a", "b", "c", "d", or None for unranked
