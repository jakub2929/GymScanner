from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re

HEX_COLOR_REGEX = re.compile(r"^#(?:[0-9a-fA-F]{6})$")

class BrandingResponse(BaseModel):
    brand_name: str
    console_name: str
    tagline: Optional[str] = None
    support_email: Optional[EmailStr] = None
    primary_color: str
    footer_text: Optional[str] = None
    logo_url: Optional[str] = None
    reservations_enabled: bool = False

class BrandingUpdateRequest(BaseModel):
    brand_name: str = Field(..., min_length=2, max_length=100)
    console_name: str = Field(..., min_length=2, max_length=100)
    tagline: Optional[str] = Field(default=None, max_length=255)
    support_email: Optional[EmailStr] = Field(default=None, max_length=255)
    primary_color: str = Field(..., description="Hex color in format #RRGGBB")
    footer_text: Optional[str] = Field(default=None, max_length=255)
    logo_url: Optional[str] = Field(default=None, max_length=512)
    reservations_enabled: bool = Field(default=False)

    @field_validator("brand_name", "console_name", mode="before")
    @classmethod
    def strip_text(cls, value: str):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("primary_color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        if not HEX_COLOR_REGEX.match(value):
            raise ValueError("Primary color must be in format #RRGGBB")
        return value.upper()
