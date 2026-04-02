"""Grafo principal de OpsAgent.

Define el flujo del pipeline de diagnostico operativo:
  START -> ingestion -> [check quality] -> analysis -> recommendations -> END
                                       -> END (si calidad < 50%)
"""

from langgraph.graph import StateGraph, START, END

from opsagent.state import OpsAgentState
from opsagent.agents.ingestion import ingestion_node
from opsagent.agents.analysis import analysis_node
from opsagent.agents.recommendations import recommendations_node


def check_ingestion_quality(state: OpsAgentState) -> str:
    """Routing: si ingestion produjo error, terminar temprano."""
    if state.get("processing_status") == "error":
        return "end"
    return "analysis"


def build_graph():
    """Construir y compilar el grafo de OpsAgent.

    Incluye conditional edge despues de ingestion:
    si la calidad de datos es < 50%, el grafo termina con error.
    """
    builder = StateGraph(OpsAgentState)

    # Registrar nodos
    builder.add_node("ingestion", ingestion_node)
    builder.add_node("analysis", analysis_node)
    builder.add_node("recommendations", recommendations_node)

    # Flujo con conditional edge
    builder.add_edge(START, "ingestion")
    builder.add_conditional_edges(
        "ingestion",
        check_ingestion_quality,
        {"analysis": "analysis", "end": END},
    )
    builder.add_edge("analysis", "recommendations")
    builder.add_edge("recommendations", END)

    return builder.compile()
