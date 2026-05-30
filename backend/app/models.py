from datetime import datetime
from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LogEntry(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    relay: Mapped[str] = mapped_column(String(80), default="mock", index=True)
    prompt: Mapped[str] = mapped_column(Text)
    response_text: Mapped[str] = mapped_column(Text)
    risk_label: Mapped[str] = mapped_column(String(20), index=True)
    risk_score: Mapped[float] = mapped_column(Float, index=True)
    drift_score: Mapped[float] = mapped_column(Float, default=0.0)
    mixed_model: Mapped[bool] = mapped_column(default=False)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    provider: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    token_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    raw_json: Mapped[dict | None] = mapped_column("raw", JSON, nullable=True)
    analysis: Mapped[dict] = mapped_column(JSON)
