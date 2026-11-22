"""Isolated SQLite/storage settings for unit and integration tests without PostgreSQL."""
from tempfile import TemporaryDirectory
import os

# Import the application settings without requiring a local .env/PostgreSQL setup.
for _key, _value in {
    "DB_NAME": "tests", "DB_USER": "tests", "DB_PASSWORD": "",
    "DB_HOST": "localhost", "DB_PORT": "5432",
}.items():
    os.environ.setdefault(_key, _value)

from .settings import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
JOB_RUNNER = "sync"
AI_PROVIDER = "fake"
os.environ["AI_PROVIDER"] = "fake"
_test_media = TemporaryDirectory(prefix="prettydocs-tests-")
MEDIA_ROOT = _test_media.name
