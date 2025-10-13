"""Interactive user creation utility for Prebetter.

This script provides a CLI interface to create regular users and superusers
in the Prebetter database with proper validation and error handling.

Usage:
    uv run python -m app.scripts.create_user
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

import typer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_user_id, get_password_hash
from app.database.config import PrebetterBase, prebetter_engine
from app.models.users import User

app = typer.Typer(help="Prebetter user management", no_args_is_help=False, add_completion=False)
logger = logging.getLogger(__name__)


def _validate_username(username: str) -> Optional[str]:
    """Validate username and return error message if invalid."""
    if len(username) < 3:
        return "Username must be at least 3 characters"
    if len(username) > 20:
        return "Username must be at most 20 characters"
    return None


def _validate_email(email: str) -> Optional[str]:
    """Validate email and return error message if invalid."""
    if "@" not in email or "." not in email.split("@")[-1]:
        return "Invalid email format"
    return None


def _validate_password(password: str) -> Optional[str]:
    """Validate password and return error message if invalid."""
    if len(password) < 8:
        return "Password must be at least 8 characters"
    return None


def _create_user_in_db(username: str, email: str, password: str, is_superuser: bool) -> bool:
    """Create user in database.

    Args:
        username: Username for the new user
        email: Email address for the new user
        password: Plain text password (will be hashed)
        is_superuser: Whether to create as superuser

    Returns:
        True if user was created successfully, False otherwise
    """
    try:
        # Ensure database and tables exist
        PrebetterBase.metadata.create_all(bind=prebetter_engine)

        with Session(prebetter_engine) as db:
            # Check if username already exists
            existing_user = db.execute(
                select(User).where(User.username == username)
            ).scalar_one_or_none()

            if existing_user:
                typer.secho(f"Error: Username '{username}' already exists!", fg=typer.colors.RED, err=True)
                return False

            # Check if email already exists
            existing_email = db.execute(
                select(User).where(User.email == email)
            ).scalar_one_or_none()

            if existing_email:
                typer.secho(f"Error: Email '{email}' is already registered!", fg=typer.colors.RED, err=True)
                return False

            # Create new user
            new_user = User(
                id=create_user_id(),
                username=username,
                email=email,
                hashed_password=get_password_hash(password),
                is_superuser=is_superuser,
            )

            db.add(new_user)
            db.commit()

            user_type = "SUPERUSER" if is_superuser else "USER"
            typer.secho(f"\n✓ {user_type} '{username}' created successfully!", fg=typer.colors.GREEN, bold=True)

            return True

    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        typer.secho(f"Error creating user: {e}", fg=typer.colors.RED, err=True)
        return False


@app.command()
def create(
    username: Optional[str] = typer.Option(None, "--username", "-u", help="Username for the new user"),
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Email address"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Password (prompted if not provided)"),
    superuser: bool = typer.Option(False, "--superuser", "-s", help="Create as superuser"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Create a new user for Prebetter.

    Interactive prompts will be used for any missing required information.
    """
    typer.secho("\n=== Create Prebetter User ===\n", bold=True)

    # Get username with validation
    if username is None:
        username = typer.prompt("Username")

    error = _validate_username(username)
    if error:
        typer.secho(f"Error: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # Get email with validation
    if email is None:
        email = typer.prompt("Email")

    error = _validate_email(email)
    if error:
        typer.secho(f"Error: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # Get password with validation
    if password is None:
        password = typer.prompt("Password", hide_input=True, confirmation_prompt=True)

    error = _validate_password(password)
    if error:
        typer.secho(f"Error: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    # Show summary
    typer.echo("\nSummary:")
    typer.echo(f"  Username: {username}")
    typer.echo(f"  Email: {email}")
    typer.echo(f"  Superuser: {'Yes' if superuser else 'No'}")

    # Confirm
    if not yes and not typer.confirm("\nProceed with user creation?"):
        typer.echo("Cancelled.")
        raise typer.Exit(code=0)

    # Create user
    success = _create_user_in_db(username, email, password, superuser)
    raise typer.Exit(code=0 if success else 1)


def main() -> None:
    """Entry point for the script."""
    logging.basicConfig(level=logging.INFO)
    app()


if __name__ == "__main__":
    main()