import asyncio
import os
import sys

from services.design_agent import run_design_agent

async def main():
    print("=========================================")
    print("  LangGraph Agent CLI 測試模式")
    print("  輸入對話，輸入 'exit' 或 'quit' 離開")
    print("=========================================\n")
    
    # Check API Key
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        print("警告: 尚未設定 OPENROUTER_API_KEY，您可能需要先在 backend/.env 或終端機中設定它！")
        return

    # Use a dummy thread ID to test MemorySaver
    thread_id = "cli-test-thread-001"
    
    messages = []
    
    while True:
        try:
            user_input = input("\n使用者> ")
        except (KeyboardInterrupt, EOFError):
            break
            
        if user_input.lower() in ["exit", "quit"]:
            break
            
        if not user_input.strip():
            continue
            
        messages.append({"role": "user", "content": user_input})
        
        print(f"\nAgent (Thread: {thread_id})> ", end="", flush=True)
        
        try:
            async for event in run_design_agent(messages, thread_id=thread_id):
                if event["type"] == "message":
                    print(event["content"], end="", flush=True)
                elif event["type"] == "progress":
                    print(f"\n[進度] {event['content']}", end="", flush=True)
                elif event["type"] == "xml":
                    print(f"\n[產生 XML (長度: {len(event['content'])})]", end="", flush=True)
                elif event["type"] == "error":
                    print(f"\n[錯誤] {event['content']}", end="", flush=True)
            print()
            
        except Exception as e:
            print(f"\n[執行例外] {e}")

if __name__ == "__main__":
    # Ensure working directory is backend/
    import os
    if not os.path.exists("services/design_agent.py"):
        print("請在 backend/ 目錄下執行此腳本！")
        sys.exit(1)
        
    asyncio.run(main())
