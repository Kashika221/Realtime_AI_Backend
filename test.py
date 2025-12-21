import asyncio
import json
import websockets
import uuid
import time

async def main():
    session_id = f"test-{uuid.uuid4().hex[:8]}"
    uri = f"ws://localhost:8000/ws/session/{session_id}"
    print("Simple WebSocket Test")
    print(f"Session ID: {session_id}")
    print(f"URI: {uri}")
    
    try:
        async with websockets.connect(uri) as ws:
            print("Connected!\n")
            print("Test 1: Sending message with tool use...")
            message = {
                "type": "message",
                "content": "Can you fetch user data for user_alice and search for Python information?"
            }
            
            print(f"Sending: {message['content']}\n")
            await ws.send(json.dumps(message))
            response_count = 0
            start_time = time.time()
            
            while True:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=15.0)
                    data = json.loads(response)
                    elapsed = time.time() - start_time
                    
                    if data.get("type") == "text":
                        response_count += 1
                        print(f"[{elapsed:.2f}s] Assistant: {data.get('content', '')}\n")
                    
                    elif data.get("type") == "tool_use":
                        print(f"[{elapsed:.2f}s] Tool Used: {data.get('tool')}")
                        print(f"    Result: {json.dumps(data.get('result'), indent=2)}\n")
                    
                    elif data.get("type") == "done":
                        print(f"[{elapsed:.2f}s] Response Complete\n")
                        break
                
                except asyncio.TimeoutError:
                    print("\nTimeout waiting for response")
                    break
            print("Test 2: Sending follow-up message...")
            
            follow_up = {
                "type": "message",
                "content": "Tell me more about what you found."
            }
            
            print(f"Sending: {follow_up['content']}\n")
            await ws.send(json.dumps(follow_up))
            
            response_count = 0
            start_time = time.time()
            
            while True:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=15.0)
                    data = json.loads(response)
                    elapsed = time.time() - start_time
                    
                    if data.get("type") == "text":
                        response_count += 1
                        print(f"[{elapsed:.2f}s] Assistant: {data.get('content', '')}\n")
                    
                    elif data.get("type") == "done":
                        print(f"[{elapsed:.2f}s] Response Complete\n")
                        break
                
                except asyncio.TimeoutError:
                    print("\nTimeout waiting for response")
                    break
            
            print(f"\nSession {session_id} completed successfully.")
            print(f"  - Sessions: SELECT * FROM sessions WHERE session_id = '{session_id}';")
            print(f"  - Events: SELECT * FROM events WHERE session_id = '{session_id}';")
            print("\n")

    except ConnectionRefusedError:
        print("  uri = f'ws://your-host:8000/ws/session/{session_id}'")
        print("\n")
    
    except Exception as e:
        print("Error")
        print(f"\nError: {type(e).__name__}")
        print(f"Message: {e}")
        print("\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user\n")