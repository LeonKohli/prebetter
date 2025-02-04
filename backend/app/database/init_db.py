from sqlalchemy import text
from .config import prebetter_engine, PrebetterBase
from ..models.users import User  # Import all models here
from ..core.security import get_password_hash, create_user_id
import logging
import asyncio

logger = logging.getLogger(__name__)

async def ensure_database() -> None:
    """Ensure database and tables exist, create superuser if needed."""
    try:
        # Create database if it doesn't exist
        with prebetter_engine.connect() as conn:
            conn.execute(text("CREATE DATABASE IF NOT EXISTS prebetter"))
            conn.execute(text("USE prebetter"))
            conn.commit()

        # Create all tables
        PrebetterBase.metadata.create_all(bind=prebetter_engine)
        
        # Create superuser if it doesn't exist
        from sqlalchemy.orm import Session
        
        db = Session(prebetter_engine)
        try:
            # Check if superuser exists
            superuser = db.query(User).filter(User.is_superuser).first()
            if not superuser:
                # Create superuser
                superuser = User(
                    id=create_user_id(),
                    email="admin@example.com",
                    username="admin",
                    hashed_password=get_password_hash("admin"),
                    is_superuser=True
                )
                db.add(superuser)
                db.commit()
                logger.info("Superuser created successfully!")
            else:
                logger.info("Superuser already exists.")
        finally:
            db.close()
            
        logger.info("Database initialization completed successfully!")
    except Exception as e:
        logger.error(f"Error during database initialization: {str(e)}")
        raise

if __name__ == "__main__":
    print("Initializing prebetter database...")
    asyncio.run(ensure_database())
    print("Database initialization completed!") 