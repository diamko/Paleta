from pathlib import Path
import sys
import os

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-32-characters-min")

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from extensions import db
from models.user import User
from models.user_contact import UserContact


@pytest.fixture()
def app(tmp_path: Path):
    db_path = tmp_path / "test.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "AUTO_CREATE_TABLES": True,
            "SESSION_COOKIE_SECURE": False,
            "JWT_SECRET_KEY": "test-jwt-secret-key-with-safe-length-32",
            "JWT_ISSUER": "paleta-test",
            "JWT_AUDIENCE": "paleta-mobile-test",
            "MAX_IMAGE_PIXELS": 2_000_000,
        }
    )

    with app.app_context():
        db.drop_all()
        db.create_all()

    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def create_user(app):
    def _create_user(username: str, password: str = "Password123!", email: str | None = None):
        with app.app_context():
            user = User(username=username, password_hash=generate_password_hash(password, method="scrypt"))
            if email:
                user.contact = UserContact(email=email)
            db.session.add(user)
            db.session.commit()
            return user.id

    return _create_user
