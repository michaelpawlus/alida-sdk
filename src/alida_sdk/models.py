"""Data models for Alida SDK resources."""

from dataclasses import dataclass, field


@dataclass
class Survey:
    """Represents an Alida survey (activity)."""

    id: str
    name: str
    status: str
    created_at: str | None = None
    updated_at: str | None = None
    type: str | None = None
    raw: dict = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "type": self.type,
            **self.raw,
        }


@dataclass
class SurveyResponse:
    """Represents a single response to a survey."""

    id: str
    survey_id: str
    data: dict = field(default_factory=dict)
    submitted_at: str | None = None
    raw: dict = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "survey_id": self.survey_id,
            "data": self.data,
            "submitted_at": self.submitted_at,
            **self.raw,
        }


@dataclass
class BatchExportStatus:
    """Tracks the status of a batch response export."""

    batch_id: str
    status: str
    download_url: str | None = None
    raw: dict = field(default_factory=dict, repr=False)
