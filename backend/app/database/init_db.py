from sqlalchemy import text
from app.database.config import prebetter_engine, prelude_engine, PrebetterBase
import logging
import asyncio
import sqlalchemy.exc

logger = logging.getLogger(__name__)


async def check_database_connections(check_prelude=True, check_prebetter=True) -> bool:
    all_successful = True

    if check_prelude:
        try:
            with prelude_engine.connect() as conn:
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
    try:
        try:
            with prebetter_engine.connect() as conn:
                conn.execute(text("CREATE DATABASE IF NOT EXISTS prebetter"))
                conn.execute(text("USE prebetter"))
                conn.commit()
        except sqlalchemy.exc.OperationalError as e:
            logger.error(f"Failed to create/use prebetter database: {str(e)}")
            pass

        try:
            PrebetterBase.metadata.create_all(bind=prebetter_engine)
            logger.info("Database tables created successfully!")
        except sqlalchemy.exc.OperationalError as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise

        logger.info("Database initialization completed successfully!")
    except Exception as e:
        logger.error(f"Error during database initialization: {str(e)}")
        raise


def check_pair_accelerator(strict: bool = True) -> bool:
    """Verify that the Prebetter_Pair accelerator is installed on the Prelude DB.

    Checks for:
    - Table presence in current schema
    - Triggers on Prelude_Address: prebetter_pair_ai and prebetter_pair_au
    - Required indexes on Prebetter_Pair

    If `strict` is True, raises RuntimeError when a requirement is missing.
    Returns True when all checks pass, False otherwise.
    """
    ok = True
    issues: list[str] = []

    try:
        with prelude_engine.connect() as conn:
            # Table presence
            tbl = conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name = 'Prebetter_Pair'"
                )
            ).scalar()
            if not tbl:
                ok = False
                issues.append("Table Prebetter_Pair is missing")

            # Triggers
            triggers = conn.execute(text("SHOW TRIGGERS LIKE 'Prelude_Address'"))
            trigger_names = (
                {row[0] for row in triggers.fetchall()} if triggers else set()
            )
            for req in ("prebetter_pair_ai", "prebetter_pair_au"):
                if req not in trigger_names:
                    ok = False
                    issues.append(f"Trigger {req} is missing on Prelude_Address")

            # Indexes (best-effort)
            idx = conn.execute(
                text(
                    "SELECT index_name, GROUP_CONCAT(column_name ORDER BY seq_in_index) cols "
                    "FROM information_schema.statistics "
                    "WHERE table_schema = DATABASE() AND table_name = 'Prebetter_Pair' "
                    "GROUP BY index_name"
                )
            ).fetchall()
            idx_map = {row[0]: (row[1] or "") for row in idx}
            required = {
                "PRIMARY": "_message_ident",
                "idx_pair_key": "pair_key",
                "idx_source": "source_ip",
                "idx_target": "target_ip",
            }
            for name, cols in required.items():
                if name not in idx_map:
                    ok = False
                    issues.append(f"Index {name} is missing on Prebetter_Pair")

    except Exception as e:
        logger.error(f"Error checking pair accelerator: {e}")
        ok = False
        issues.append(str(e))

    if not ok:
        msg = (
            "; ".join(issues) if issues else "Prebetter_Pair accelerator not available"
        )
        if strict:
            raise RuntimeError(msg)
        logger.warning(msg)
    else:
        logger.info("Prebetter_Pair accelerator is present (table, triggers, indexes)")

    return ok


if __name__ == "__main__":
    print("Initializing prebetter database...")
    asyncio.run(ensure_database())
    print("Database initialization completed!")
