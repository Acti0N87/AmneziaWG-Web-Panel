"""Generate credentials locally on the managed host without logging secrets."""
import os
from pathlib import Path
import secrets
import sys

import bcrypt

os.umask(0o077)
directory = Path(sys.argv[1])
password_file = directory / "password.txt"
if not password_file.exists():
    password_file.write_text(secrets.token_urlsafe(32) + "\n")
password = password_file.read_text().strip().encode()
(directory / "password.hash").write_bytes(bcrypt.hashpw(password, bcrypt.gensalt(12)) + b"\n")
