from sqlalchemy import text
from app.database.config import prebetter_engine, prelude_engine, PrebetterBase
from app.models.users import User  # Import all models here
from app.core.security import get_password_hash, create_user_id
import logging
import asyncio
import sqlalchemy.exc

logger = logging.getLogger(__name__)


async def check_database_connections(check_prelude=True, check_prebetter=True) -> bool:
    """
    Check database connections.

    Args:
        check_prelude: Whether to check the Prelude database connection
        check_prebetter: Whether to check the Prebetter database connection

    Returns:
        bool: True if all requested connections are successful, False otherwise
    """
    all_successful = True

    if check_prelude:
        try:
            with prelude_engine.connect() as conn:
                # Simple query to test connection
                conn.execute(text("SELECT 1"))
                logger.info("Prelude database connection successful")
        except sqlalchemy.exc.OperationalError as e:
            logger.error(f"Prelude database connection failed: {str(e)}")
            all_successful = False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Prelude database: {str(e)}")
            all_successful = False

    if check_prebetter:
        try:
            with prebetter_engine.connect() as conn:
                # Simple query to test connection
                conn.execute(text("SELECT 1"))
                logger.info("Prebetter database connection successful")
        except sqlalchemy.exc.OperationalError as e:
            logger.error(f"Prebetter database connection failed: {str(e)}")
            all_successful = False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Prebetter database: {str(e)}")
            all_successful = False

    return all_successful


async def ensure_database() -> None:
    """Ensure prebetter database and tables exist, create superuser if needed."""
    try:
        # Create database if it doesn't exist
        try:
            with prebetter_engine.connect() as conn:
                conn.execute(text("CREATE DATABASE IF NOT EXISTS prebetter"))
                conn.execute(text("USE prebetter"))
                conn.commit()
        except sqlalchemy.exc.OperationalError as e:
            logger.error(f"Failed to create/use prebetter database: {str(e)}")
            # Continue anyway to handle cases where database exists but cannot be created
            # (e.g., insufficient privileges)
            pass

        # Create all tables
        try:
            PrebetterBase.metadata.create_all(bind=prebetter_engine)
        except sqlalchemy.exc.OperationalError as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise

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
                    is_superuser=True,
                )
                db.add(superuser)
                db.commit()
                logger.info("Superuser created successfully!")
            else:
                logger.info("Superuser already exists.")
        except Exception as e:
            logger.error(f"Error checking/creating superuser: {str(e)}")
            db.rollback()
            raise
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
