from pydantic import BaseModel, Field, field_validator
from typing import Optional


class Drama(BaseModel):
    title: str
    year: int
    role: str = ""
    poster: Optional[str] = None
    category: str = "drama"  # "drama" or "show"


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


VALID_TIERS = {"splus", "s", "a", "b", "c", "d"}


class TierUpdate(BaseModel):
    tier: Optional[str] = None  # "splus", "s", "a", "b", "c", "d", or None for unranked

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_TIERS:
            raise ValueError(f"Invalid tier '{v}'. Must be one of: {', '.join(sorted(VALID_TIERS))}")
        return v


class ProfileUpdate(BaseModel):
    displayName: Optional[str] = None
    bio: Optional[str] = None
    shareSlug: Optional[str] = None
    tierListVisibility: Optional[str] = None  # "private", "link_only", "public"
