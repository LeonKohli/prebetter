# Prebetter Management Scripts

Management commands for Prebetter.

## Available Commands

### create_user.py
Creates users for the system.

```bash
python -m app.scripts.create_user
```

The script will prompt for:
- Username
- Email
- Password (hidden input, min 8 chars)
- Whether to create as superuser (admin)

## Security Notes

- No default credentials are created automatically
- Passwords must be at least 8 characters
- Superuser accounts have full admin privileges