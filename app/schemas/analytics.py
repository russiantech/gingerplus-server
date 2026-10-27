from pydantic import BaseModel, Field


class TrackEvent(BaseModel):
    session_id: str = Field(min_length=8, max_length=64)
    path: str = Field(max_length=500)
    referrer: str | None = Field(default=None, max_length=500)
    utm_source: str | None = None
