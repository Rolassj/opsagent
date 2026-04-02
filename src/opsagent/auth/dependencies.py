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

    Si SUPABASE_JWT_SECRET no esta configurado, retorna "anonymous"
    (modo desarrollo sin auth).
    """
    if not settings.auth_enabled:
        return "anonymous"

    if credentials is None:
        raise HTTPException(status_code=401, detail="Token de autenticacion requerido")

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalido")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token sin user_id")
    return user_id
