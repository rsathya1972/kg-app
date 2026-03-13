from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    environment: str
    db_status: str
    message: Optional[str] = None
