#!/usr/bin/env python
"""
Simple user creation script for Prebetter.

Usage:
    python -m app.scripts.create_user
"""
import sys
import asyncio
from sqlalchemy import select
from sqlalchemy.orm import Session
import click

from app.database.config import prebetter_engine, PrebetterBase
from app.models.users import User
from app.core.security import get_password_hash, create_user_id
import logging

logger = logging.getLogger(__name__)


async def create_user_in_db(username: str, email: str, password: str, is_superuser: bool) -> bool:
    """Create user in database."""
    try:
        # Ensure database and tables exist
        PrebetterBase.metadata.create_all(bind=prebetter_engine)

        db = Session(prebetter_engine)
        try:
            # Check if username already exists
            existing_user = db.execute(
                select(User).where(User.username == username)
            ).scalar_one_or_none()

            if existing_user:
                click.echo(click.style(f"Error: Username '{username}' already exists!", fg='red'), err=True)
                return False

            # Check if email already exists
            existing_email = db.execute(
                select(User).where(User.email == email)
            ).scalar_one_or_none()

            if existing_email:
                click.echo(click.style(f"Error: Email '{email}' is already registered!", fg='red'), err=True)
                return False

            # Create new user
            new_user = User(
                id=create_user_id(),
                username=username,
                email=email,
                hashed_password=get_password_hash(password),
                is_superuser=is_superuser
            )

            db.add(new_user)
            db.commit()

            user_type = "SUPERUSER" if is_superuser else "USER"
            click.echo(click.style(f"\n✓ {user_type} '{username}' created successfully!", fg='green', bold=True))

            return True

        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            click.echo(click.style(f"Error creating user: {str(e)}", fg='red'), err=True)
            db.rollback()
            return False
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        click.echo(click.style(f"Database connection failed: {str(e)}", fg='red'), err=True)
        return False


@click.command()
def create_user():
    """Create a user for Prebetter."""
    click.echo(click.style('\n=== Create Prebetter User ===\n', bold=True))

    # Get username
    username = click.prompt('Username')
    if len(username) < 3 or len(username) > 20:
        click.echo(click.style('Username must be 3-20 characters', fg='red'))
        sys.exit(1)

    # Get email
    email = click.prompt('Email')
    if '@' not in email:
        click.echo(click.style('Invalid email format', fg='red'))
        sys.exit(1)

    # Get password
    password = click.prompt('Password', hide_input=True, confirmation_prompt=True)
    if len(password) < 8:
        click.echo(click.style('Password must be at least 8 characters', fg='red'))
        sys.exit(1)

    # Ask for superuser
    is_superuser = click.confirm('Create as superuser (admin)?', default=False)

    # Show summary
    click.echo("\nSummary:")
    click.echo(f"  Username: {username}")
    click.echo(f"  Email: {email}")
    click.echo(f"  Superuser: {'Yes' if is_superuser else 'No'}")

    # Confirm
    if not click.confirm('\nProceed with user creation?'):
        click.echo('Cancelled.')
        sys.exit(0)

    # Create user
    success = asyncio.run(create_user_in_db(username, email, password, is_superuser))
    sys.exit(0 if success else 1)


def main():
    """Entry point."""
    try:
        create_user()
    except KeyboardInterrupt:
        click.echo("\n\nCancelled.")
        sys.exit(1)
    except click.Abort:
        click.echo("\nCancelled.")
        sys.exit(1)


if __name__ == "__main__":
    main()