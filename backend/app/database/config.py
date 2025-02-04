from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import Generator
from ..core.config import get_settings

settings = get_settings()

# Create SQLAlchemy engines for both databases
prelude_engine = create_engine(
    settings.PRELUDE_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
)

prebetter_engine = create_engine(
    settings.PREBETTER_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
)

# Create metadata objects
prelude_metadata = MetaData()
prelude_metadata.bind = prelude_engine

prebetter_metadata = MetaData()
prebetter_metadata.bind = prebetter_engine

# Create session factories
PreludeSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=prelude_engine)
PrebetterSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=prebetter_engine)

# Create base classes for declarative models
PreludeBase = declarative_base(metadata=prelude_metadata)
PrebetterBase = declarative_base(metadata=prebetter_metadata)

def get_prelude_db() -> Generator[Session, None, None]:
    """Dependency for getting prelude database session"""
    db = PreludeSessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_prebetter_db() -> Generator[Session, None, None]:
    """Dependency for getting prebetter database session"""
    db = PrebetterSessionLocal()
    try:
        yield db
    finally:
        db.close()
