from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# Setup SQLAlchemy engine (synchronous)
# synchronous engine is used since Celery and standard FastAPI routes can use standard sync ORM.
engine = create_engine(
    settings.sqlalchemy_database_url,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
