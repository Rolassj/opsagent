"""Agentes de OpsAgent.

Cada agente es una función nodo para LangGraph.
Se construyen y validan de forma independiente antes de conectarse al grafo.

MVP:
- ingestion: carga y normaliza datos CSV/Excel
- analysis: calcula KPIs y detecta anomalías
- recommendations: genera diagnóstico con Claude
"""
