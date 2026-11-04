"""
SkillSaathi Graph State Definition
Typed state schema for LangGraph multi-agent family career counselling (SIH26241).
"""

from typing import TypedDict, Annotated, Sequence, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class CounsellingState(TypedDict, total=False):
    """
    Centralized state for the multi-agent family counselling session.
    Tracks dialogue turns, evidence discovered by tools, identified disputes,
    and synthesized consensus pathways.
    """
    family_id: str
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # Ingested profiles & evidence
    student_profile: Dict[str, Any]
    parent_profile: Dict[str, Any]
    retrieved_courses: List[Dict[str, Any]]
    
    # Specialist agent findings
    student_advocate_notes: str
    parent_liaison_notes: str
    verified_facts: List[Dict[str, Any]]
    
    # Mediation & consensus outputs
    shared_strengths: List[Dict[str, Any]]
    disagreements: List[Dict[str, Any]]
    compromises: List[Dict[str, Any]]
    consensus_readiness: str  # "high" | "moderate" | "requires_dialogue"
    
    # Orchestrator control flags
    next_speaker: str  # "student_advocate" | "parent_liaison" | "fact_checker" | "mediator" | "finish" | "escalate"
    iteration_count: int
    human_escalation_needed: bool
    escalation_reason: Optional[str]
    model_name: Optional[str]
    strict: bool
    error: Optional[str]
    
    # Final structured report adhering to ConsensusSummaryResponse schema
    final_consensus_summary: Optional[Dict[str, Any]]

