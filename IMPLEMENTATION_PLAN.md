# SkillSaathi — Multi-Agent LangChain & LangGraph Implementation Plan

**Problem Statement:** SIH26241 (AI-Enabled Career Counselling & Family Decision-Support for Vocational Education)  
**Architecture:** LangChain + LangGraph Multi-Agent Stateful Orchestration with Gemini 3.8 Flash & NCrF Policy Tools.

---

## Progress Overview
- [x] **Phase 1: Foundation, Dependencies & LangChain Model Setup**
- [x] **Phase 2: Dynamic Tool Ecosystem & Hybrid RAG Retrieval**
- [x] **Phase 3: Multi-Agent Personas & Node Implementation**
- [x] **Phase 4: LangGraph State Machine, Supervisor & HITL Compilation**
- [x] **Phase 5: FastAPI Backend Route & WebSocket Streaming Integration**
- [x] **Phase 6: Frontend Tri-Party Negotiation UI & Real-Time Visualization**
- [x] **Phase 7: End-to-End Verification, Automated Tests & Demonstration Scenarios**

---

## Detailed Phases

### Phase 1: Foundation, Dependencies & LangChain Model Setup
- [x] **1.1** Update `backend/requirements.txt` with required libraries:
  - `langchain>=0.3.0`
  - `langchain-core>=0.3.0`
  - `langchain-google-genai>=2.0.0`
  - `langgraph>=0.2.0`
  - `langgraph-checkpoint-sqlite>=2.0.0`
  - `rank-bm25>=0.2.2`
- [x] **1.2** Install dependencies inside `.venv`.
- [x] **1.3** Create `backend/app/agents/` package structure (`__init__.py`).
- [x] **1.4** Build `backend/app/agents/llm.py` configuring Gemini (`ChatGoogleGenerativeAI` with fallback and retry logic).

---

### Phase 2: Dynamic Tool Ecosystem & Hybrid RAG Retrieval
- [x] **2.1** Create `backend/app/agents/tools.py` implementing LangChain `@tool` definitions:
  - `calculate_roi_and_breakeven`: Computes fee recovery timeline based on starting salary.
  - `fetch_district_wage_benchmark`: Queries realistic entry-level vocational earnings.
  - `calculate_ncrf_credit_ladder`: Maps ITI/NSQF credits to Polytechnic Diplomas and B.Voc degrees.
  - `search_government_schemes`: Queries PMKVY, NAPS apprenticeship stipends, and fee concessions.
- [x] **2.2** Upgrade `backend/app/rag_retriever.py` to use LangChain's `EnsembleRetriever`:
  - Dense retrieval via `GoogleGenerativeAIEmbeddings` (`gemini-embedding-2`).
  - Lexical retrieval via `BM25Retriever` for exact trade names and codes.
  - Retain zero-crash deterministic fallback for offline/no-key mode.

---

### Phase 3: Multi-Agent Personas & Node Implementation
- [x] **3.1** Define typed graph state in `backend/app/agents/state.py`:
  - `CounsellingState` (messages, student_profile, parent_profile, disagreements, verified_facts, recommendations, consensus_readiness, escalation_flag).
- [x] **3.2** Create system prompts in `backend/app/agents/prompts.py`:
  - Supervisor / Orchestrator prompt
  - Student Advocate prompt
  - Parent Liaison prompt
  - Fact-Checker & Policy Navigator prompt
  - Family Consensus Mediator prompt
- [x] **3.3** Implement agent nodes in `backend/app/agents/nodes.py`:
  - `supervisor_node`: Analyzes state and routes execution.
  - `student_advocate_node`: Extracts aspirations and builds growth cases.
  - `parent_liaison_node`: Addresses stability, financial, and degree progression concerns.
  - `fact_checker_node`: Executes tools and binds grounded evidence to the state.
  - `mediator_node`: Formulates win-win compromises and final consensus reports.

---

### Phase 4: LangGraph State Machine, Supervisor & HITL Compilation
- [x] **4.1** Implement `backend/app/agents/graph.py`:
  - Initialize `StateGraph(CounsellingState)`.
  - Add nodes (`supervisor`, `student_advocate`, `parent_liaison`, `fact_checker`, `mediator`).
  - Add conditional edges from `supervisor` to specialist nodes.
  - Implement loopback to supervisor after agent actions.
- [x] **4.2** Add Human-In-The-Loop (HITL) interrupt on severe unresolvable deadlocks.
- [x] **4.3** Connect `SqliteSaver` checkpointer for state persistence and time-travel capability.
- [x] **4.4** Verify graph compilation and standalone test execution with sample student/parent profiles.

---

### Phase 5: FastAPI Backend Route & WebSocket Streaming Integration
- [x] **5.1** Update `backend/app/routes.py`:
  - Refactor `POST /api/families/{family_id}/analyze` to execute the compiled LangGraph workflow.
  - Maintain full backward compatibility with existing `ConsensusSummaryResponse` schema.
- [x] **5.2** Add interactive conversational endpoint:
  - `POST /api/families/{family_id}/chat` for multi-turn family mediation dialogue.
- [x] **5.3** Add human counsellor resume endpoint:
  - `POST /api/families/{family_id}/resume` to unblock interrupted graphs after human intervention.
- [x] **5.4** Add streaming endpoint / WebSocket support for real-time token generation.

---

### Phase 6: Frontend Tri-Party Negotiation UI & Real-Time Visualization
- [x] **6.1** Connect the frontend counselling view to the new LangGraph multi-turn endpoint.
- [x] **6.2** Build agent speech indicators displaying who is speaking (Student Advocate, Parent Liaison, Fact-Checker, Mediator).
- [x] **6.3** Add interactive NCrF Credit Progression Ladder component in the career pathways view.
- [x] **6.4** Add Live Consensus Readiness meter reflecting real-time agreement level.

---

### Phase 7: End-to-End Verification, Automated Tests & Demonstration Scenarios
- [x] **7.1** Write pytest integration tests in `backend/tests/test_langgraph_counselling.py` and `backend/tests/test_counselling_scenarios.py`.
- [x] **7.2** Test edge cases:
  - Complete alignment (immediate consensus).
  - High friction / disagreement (successful mediation via Dual VET / NCrF bridge).
  - Severe deadlock (HITL trigger and counsellor escalation).
  - Offline fallback (no API key).
- [x] **7.3** Full end-to-end smoke test between frontend and backend.

