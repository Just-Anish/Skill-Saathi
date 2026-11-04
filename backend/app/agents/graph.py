"""
SkillSaathi LangGraph State Machine & Orchestrator
Compiles the multi-agent graph with cyclical feedback, SQLite checkpointing, and HITL interrupts (SIH26241).
"""

import os
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Generator

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from .state import CounsellingState
from .nodes import (
    supervisor_node,
    student_advocate_node,
    parent_liaison_node,
    fact_checker_node,
    mediator_node,
    human_escalation_node
)

logger = logging.getLogger("skillsaathi.agents.graph")

# Persistent checkpoint storage directory
_DB_PATH = Path(__file__).resolve().parent.parent.parent / "skillsaathi_checkpoints.db"


def _route_supervisor(state: CounsellingState) -> str:
    """Conditional edge routing based on supervisor decision."""
    speaker = state.get("next_speaker", "mediator")
    return speaker


def build_counselling_graph(
    checkpointer: Optional[SqliteSaver] = None,
    enable_hitl: bool = True
):
    """
    Constructs and compiles the full multi-agent counselling StateGraph.
    
    Nodes:
      - supervisor: Central turn router and deadlock evaluator
      - student_advocate: Youth champion for practical sunrise trades
      - parent_liaison: Family elder advocate for security and fees
      - fact_checker: Executes NCrF and economic tools
      - mediator: Synthesizes win-win compromises & consensus report
      - escalation: Human-in-the-loop pause node
    """
    builder = StateGraph(CounsellingState)

    # Register Nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("student_advocate", student_advocate_node)
    builder.add_node("parent_liaison", parent_liaison_node)
    builder.add_node("fact_checker", fact_checker_node)
    builder.add_node("mediator", mediator_node)
    builder.add_node("escalation", human_escalation_node)

    # Entry edge
    builder.add_edge(START, "supervisor")

    # Conditional branching from supervisor
    builder.add_conditional_edges(
        "supervisor",
        _route_supervisor,
        {
            "student_advocate": "student_advocate",
            "parent_liaison": "parent_liaison",
            "fact_checker": "fact_checker",
            "mediator": "mediator",
            "escalate": "escalation",
            "finish": END
        }
    )

    # Cyclical loopbacks: specialist agents report back to supervisor
    builder.add_edge("student_advocate", "supervisor")
    builder.add_edge("parent_liaison", "supervisor")
    builder.add_edge("fact_checker", "supervisor")
    
    # Terminal edges
    builder.add_edge("mediator", END)
    builder.add_edge("escalation", END)

    # Checkpointer configuration
    if checkpointer is None:
        try:
            conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
            checkpointer = SqliteSaver(conn)
        except Exception as exc:
            logger.warning("[Graph] Failed to open SQLite checkpointer file %s: %s. Using in-memory.", _DB_PATH, exc)
            conn = sqlite3.connect(":memory:", check_same_thread=False)
            checkpointer = SqliteSaver(conn)

    # Compile with HITL interrupt before escalation if enabled
    interrupts = ["escalation"] if enable_hitl else []
    return builder.compile(checkpointer=checkpointer, interrupt_before=interrupts)


# Singleton compiled graph instance
counselling_graph = build_counselling_graph()


def run_family_counselling(
    family_id: str,
    student_profile: Dict[str, Any],
    parent_profile: Dict[str, Any],
    courses: List[Dict[str, Any]],
    thread_id: Optional[str] = None,
    model_name: Optional[str] = None,
    strict: bool = False
) -> Dict[str, Any]:
    """
    Synchronous execution helper for running the full multi-agent consensus workflow.
    Returns the final state containing the consensus report and message history.
    """
    effective_thread_id = thread_id or family_id
    config = {"configurable": {"thread_id": effective_thread_id}}

    initial_state: CounsellingState = {
        "family_id": family_id,
        "messages": [],
        "student_profile": student_profile,
        "parent_profile": parent_profile,
        "retrieved_courses": courses,
        "iteration_count": 0,
        "human_escalation_needed": False,
        "model_name": model_name,
        "strict": strict
    }

    final_state = counselling_graph.invoke(initial_state, config=config)
    return final_state


def get_counselling_state(thread_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve the snapshot state for a given session thread."""
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = counselling_graph.get_state(config)
    if snapshot and snapshot.values:
        return snapshot.values
    return None


def resume_counselling_session(
    thread_id: str,
    counsellor_notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Resumes an interrupted session after human counselor intervention.
    """
    config = {"configurable": {"thread_id": thread_id}}
    
    if counsellor_notes:
        counselling_graph.update_state(
            config,
            {"escalation_reason": counsellor_notes, "human_escalation_needed": False}
        )

    # Resume graph execution from pause point
    resumed_state = counselling_graph.invoke(None, config=config)
    return resumed_state

