"""Tests para la validacion JWT de Supabase."""

import time
import pytest
import jwt
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from opsagent.auth.dependencies import get_current_user

JWT_SECRET = "test-secret-for-testing-only"


def _make_token(user_id: str = "user-123", expired: bool = False) -> str:
    """Generar un JWT de prueba."""
    payload = {
        "sub": user_id,
        "aud": "authenticated",
        "exp": int(time.time()) + (-3600 if expired else 3600),
        "iat": int(time.time()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


# Crear una app separada para tests de auth (sin dependency overrides)
from opsagent.api.main import app as _original_app

auth_app = FastAPI()


@auth_app.get("/health")
async def health():
    return {"status": "ok"}


@auth_app.get("/diagnoses")
async def diagnoses(user_id: str = pytest.importorskip("fastapi").Depends(get_current_user)):
    return []


# Use a fresh test client that doesn't share overrides with test_routes
from fastapi import Depends


auth_test_app = FastAPI()


@auth_test_app.get("/health")
async def auth_health(user_id: str = Depends(get_current_user)):
    return {"status": "ok"}


@auth_test_app.get("/diagnoses")
async def auth_diagnoses(user_id: str = Depends(get_current_user)):
    return []


client_auth = TestClient(auth_test_app)


def test_auth_token_valido():
    """Request con token valido retorna 200."""
    token = _make_token("user-abc")
    with patch("opsagent.auth.dependencies.settings") as mock_settings:
        mock_settings.auth_enabled = True
        mock_settings.SUPABASE_JWT_SECRET = JWT_SECRET
        response = client_auth.get("/health", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_auth_sin_token_modo_dev():
    """Sin SUPABASE_JWT_SECRET configurado, requests pasan como anonymous."""
    with patch("opsagent.auth.dependencies.settings") as mock_settings:
        mock_settings.auth_enabled = False
        response = client_auth.get("/diagnoses")
    assert response.status_code == 200


def test_auth_token_expirado():
    """Request con token expirado retorna 401."""
    token = _make_token(expired=True)
    with patch("opsagent.auth.dependencies.settings") as mock_settings:
        mock_settings.auth_enabled = True
        mock_settings.SUPABASE_JWT_SECRET = JWT_SECRET
        response = client_auth.get("/diagnoses", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_auth_token_invalido():
    """Request con token mal formado retorna 401."""
    with patch("opsagent.auth.dependencies.settings") as mock_settings:
        mock_settings.auth_enabled = True
        mock_settings.SUPABASE_JWT_SECRET = JWT_SECRET
        response = client_auth.get("/diagnoses", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
