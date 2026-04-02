"""Configuracion global de pytest para OpsAgent."""

import os
from dotenv import load_dotenv

# Cargar .env desde la raiz del proyecto para que los integration tests
# tengan acceso a ANTHROPIC_API_KEY sin necesidad de exportarla manualmente.
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)
