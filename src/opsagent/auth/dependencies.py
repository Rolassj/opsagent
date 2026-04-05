"""Dependencias de autenticacion para FastAPI."""

from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from opsagent.config import settings

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """Validar JWT de Supabase y retornar user_id.

    Si no hay credentials o auth_enabled es False, retorna "anonymous"
    (permite acceso público sin autenticación).
    """
    # Si auth no está habilitado, retornar anonymous
    if not settings.auth_enabled:
        return "anonymous"

    # Si no hay credentials, retornar anonymous (acceso público)
    if credentials is None:
        return "anonymous"

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        # Token expirado: retornar anonymous en lugar de lanzar excepción
        return "anonymous"
    except jwt.InvalidTokenError:
        # Token inválido: retornar anonymous en lugar de lanzar excepción
        return "anonymous"

    user_id = payload.get("sub")
    if not user_id:
        # Sin user_id en token: retornar anonymous
        return "anonymous"
    return user_id
