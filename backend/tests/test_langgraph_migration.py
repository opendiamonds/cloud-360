import unittest
from unittest.mock import patch, MagicMock
import asyncio

from langchain_core.messages import HumanMessage, AIMessage

from services.design_agent import build_graph, memory

class TestLangGraphMigration(unittest.IsolatedAsyncioTestCase):
    @patch("services.design_agent.ChatAnthropic")
    @patch("services.design_agent.get_design_model_name")
    @patch("services.design_agent.configure_provider_env")
    async def test_langgraph_memory(self, mock_env, mock_model, mock_chat):
        mock_model.return_value = "claude-3-5-sonnet-20240620"
        
        mock_llm_instance = MagicMock()
        async def mock_ainvoke(*args, **kwargs):
            return AIMessage(content="I understand. I will help you.")
        mock_llm_instance.ainvoke = mock_ainvoke
        
        mock_llm_instance.bind_tools.return_value = mock_llm_instance
        mock_chat.return_value = mock_llm_instance

        graph = build_graph().compile(checkpointer=memory)
        config = {"configurable": {"thread_id": "test-thread-1"}}
        
        initial_state = {"messages": [HumanMessage(content="Hello!")]}
        
        # Run graph
        async for event in graph.astream(initial_state, config=config, stream_mode="values"):
            pass
            
        saved_state = graph.get_state(config)
        self.assertGreater(len(saved_state.values["messages"]), 1)
        
        # Follow up
        follow_up_state = {"messages": [HumanMessage(content="Follow up")]}
        async for event in graph.astream(follow_up_state, config=config, stream_mode="values"):
            pass
            
        final_state = graph.get_state(config)
        self.assertGreaterEqual(len(final_state.values["messages"]), 4)

if __name__ == "__main__":
    unittest.main()
