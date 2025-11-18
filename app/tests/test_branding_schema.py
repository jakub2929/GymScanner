from pydantic import ValidationError
from app.schemas.branding import BrandingUpdateRequest

def test_branding_update_accepts_valid_color():
    payload = {
        "brand_name": "Test Brand",
        "console_name": "Console",
        "primary_color": "#0EA5E9",
    }
    data = BrandingUpdateRequest(**payload)
    assert data.primary_color == "#0EA5E9"

def test_branding_update_rejects_invalid_hex():
    payload = {
        "brand_name": "Test Brand",
        "console_name": "Console",
        "primary_color": "blue",
    }
    try:
        BrandingUpdateRequest(**payload)
    except ValidationError as exc:
        assert "Primary color must be in format" in str(exc)
    else:
        raise AssertionError("ValidationError not raised for invalid color")
