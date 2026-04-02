"""Configuracion centralizada de OpsAgent."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Settings del sistema. Leer del entorno, nunca hardcodear."""

    # LLM
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    # Base de datos
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Servidor
    PORT: int = int(os.getenv("PORT", "8000"))

    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")

    @property
    def db_enabled(self) -> bool:
        """True si DATABASE_URL esta configurado."""
        return bool(self.DATABASE_URL)

    @property
    def auth_enabled(self) -> bool:
        """True si Supabase JWT esta configurado."""
        return bool(self.SUPABASE_JWT_SECRET)

    def validate(self) -> None:
        """Validar que los settings criticos esten configurados."""
        if not self.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY no configurada. "
                "Copia .env.example a .env y agrega tu API key."
            )


settings = Settings()
