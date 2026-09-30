# Unit Test Instructions

## Test Strategy (Minimal)
Since this is a POC scope, we generate only the required unit tests for the core logic we modified.

## How to Run Tests
Execute the Python `unittest` framework to verify LangGraph execution flow:
```bash
cd backend
python3 -m unittest tests.test_langgraph_migration
```

## Expected Coverage
- 1 Test verifying the `LangGraph` memory states are persisted between calls.
