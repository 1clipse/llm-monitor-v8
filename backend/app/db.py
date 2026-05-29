from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models import Base, LogEntry


settings = get_settings()
engine_kwargs = {}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, future=True, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_log(db: Session, payload: dict) -> LogEntry:
    entry = LogEntry(
        relay=payload.get("relay", "mock"),
        prompt=payload["prompt"],
        response_text=payload["text"],
        risk_label=payload["analysis"]["risk_label"],
        risk_score=payload["analysis"]["risk_score"],
        drift_score=payload["analysis"].get("drift_score", 0.0),
        mixed_model=payload["analysis"].get("mixed_model", False),
        analysis=payload["analysis"],
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_recent_logs(db: Session, limit: int = 100) -> list[LogEntry]:
    return db.query(LogEntry).order_by(LogEntry.id.desc()).limit(limit).all()
