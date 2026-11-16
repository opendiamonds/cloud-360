# Code Generation Plan: LangGraph Migration POC

- [x] **Step 1:** Update dependencies (`backend/requirements.txt`) to include `langgraph`, `langchain-core`, and `langchain-anthropic`.
- [x] **Step 2:** Refactor `backend/services/diagram_builder.py` to use LangGraph's `StateGraph`, nodes, and standard `ToolNode` pattern.
- [x] **Step 3:** Implement LangGraph state checkpointing (Memory) in `backend/services/agent_router.py` to allow persistence of workflows.
- [x] **Step 4:** Adapt other active agents (e.g., `design_agent.py`, `wa_rule_engine.py`) to the new framework.
- [x] **Step 5:** Write unit tests in `backend/tests/test_langgraph_migration.py` to verify the state transition and memory restoration.
