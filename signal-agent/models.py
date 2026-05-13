import hashlib
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class StudentSignal(BaseModel):
    id: str = ""
    source: str
    external_id: str
    name: str
    email: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    project_name: Optional[str] = None
    project_url: Optional[str] = None
    project_description: Optional[str] = None
    competition: Optional[str] = None
    school: Optional[str] = None
    location: Optional[str] = None
    relevance_score: Optional[float] = None
    score_reason: Optional[str] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    raw_data: dict = Field(default_factory=dict)

    def model_post_init(self, __context):
        if not self.id:
            self.id = hashlib.sha256(
                f"{self.source}:{self.external_id}".encode()
            ).hexdigest()[:16]
