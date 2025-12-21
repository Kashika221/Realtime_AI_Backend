import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Optional
import uuid
from contextlib import asynccontextmanager

from groq import Groq
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from supabase import create_client, Client
import uvicorn
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-project.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-anon-key")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

supabase: Client = None
groq_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global supabase, groq_client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    groq_client = Groq(api_key=GROQ_API_KEY)
    await init_db()
    print("Database initialized")
    yield
    print("Shutting down...")

app = FastAPI(
    title="Async LLM Backend with Groq",
    description="Ultra-fast conversational backend with WebSocket streaming, tool calling, and Groq LLM integration",
    version="1.0.0",
    lifespan=lifespan
)

async def init_db():
    try:
        # Check sessions table
        supabase.table("sessions").select("id").limit(1).execute()
        print("Sessions table exists")
    except Exception as e:
        print(f"Sessions table not found: {e}")
        print("MANUAL SETUP REQUIRED")
        raise
    try:
        # Check events table
        supabase.table("events").select("id").limit(1).execute()
        print("Events table exists")
    except Exception as e:
        print(f"Events table not found: {e}")
        print("MANUAL SETUP REQUIRED")
        raise

class ConversationState:
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.messages: list = []
        self.event_sequence = 0
        self.start_time = datetime.now(timezone.utc)

    async def add_event(
        self,
        event_type: str,
        role: Optional[str] = None,
        content: Optional[str] = None,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_result: Optional[str] = None,
    ):
        self.event_sequence += 1
        event_data = {
            "session_id": self.session_id,
            "event_type": event_type,
            "role": role,
            "content": content,
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "tool_result": tool_result,
            "sequence_num": self.event_sequence,
        }
        try:
            supabase.table("events").insert(event_data).execute()
        except Exception as e:
            print(f"Error logging event: {e}")

async def fetch_user_data(user_id: str) -> dict:
    await asyncio.sleep(0.5) 
    return {
        "user_id": user_id,
        "name": f"User_{user_id[:8]}",
        "tier": "premium",
        "created_at": "2024-01-15",
    }

async def search_knowledge_base(query: str) -> dict:
    await asyncio.sleep(0.3)
    return {"results": [f"Result for '{query}' #1", f"Result for '{query}' #2"]}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_user_data",
            "description": "Fetch detailed user profile and subscription information",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The user ID to fetch data for"
                    }
                },
                "required": ["user_id"],
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Search internal knowledge base for information about a topic",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query or topic to look up"
                    }
                },
                "required": ["query"],
            },
        }
    },
]

async def process_tool_call(tool_name: str, tool_input: dict) -> str:
    if tool_name == "fetch_user_data":
        result = await fetch_user_data(tool_input["user_id"])
    elif tool_name == "search_knowledge_base":
        result = await search_knowledge_base(tool_input["query"])
    else:
        result = {"error": "Unknown tool"}
    return json.dumps(result)

async def stream_llm_response(
    state: ConversationState, messages: list, websocket: WebSocket
):
    system_prompt = """You are a helpful assistant. When users ask about user data or knowledge base searches:
- Use fetch_user_data tool for user information
- Use search_knowledge_base tool for knowledge lookups
Answer based on tool results."""
    
    iteration = 0
    max_iterations = 3

    while iteration < max_iterations:
        iteration += 1

        if iteration == 1:
            groq_messages = [
                {"role": "user", "content": system_prompt}
            ]
            groq_messages.extend(messages)
        else:
            groq_messages = messages.copy()

        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=1024,
                tools=TOOLS,
                tool_choice="auto",
                messages=groq_messages,
            )
        except Exception as e:
            print(f"Groq API error: {e}")
            await websocket.send_json({"type": "error", "content": str(e)})
            break

        has_tool_use = False
        response_text = ""
        
        if response.choices[0].message.content:
            response_text = response.choices[0].message.content.strip()
            if response_text and not response_text.startswith("I'll"):
                await state.add_event(
                    "assistant_message", role="assistant", content=response_text
                )
                await websocket.send_json(
                    {"type": "text", "content": response_text, "chunk": True}
                )

        if response_text:
            messages.append({
                "role": "assistant",
                "content": response_text,
            })

        if response.choices[0].message.tool_calls:
            has_tool_use = True
            tool_calls_list = response.choices[0].message.tool_calls
            
            for tool_call in tool_calls_list:
                tool_use_id = tool_call.id
                tool_name = tool_call.function.name
                
                try:
                    tool_input = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    tool_input = {}
                    print(f"Failed to parse tool arguments: {tool_call.function.arguments}")

                await state.add_event(
                    "tool_call",
                    tool_call_id=tool_use_id,
                    tool_name=tool_name,
                    content=json.dumps(tool_input),
                )

                try:
                    tool_result = await process_tool_call(tool_name, tool_input)
                except Exception as e:
                    tool_result = json.dumps({"error": str(e)})
                    print(f"Tool execution error: {e}")

                await state.add_event(
                    "tool_result",
                    tool_call_id=tool_use_id,
                    tool_name=tool_name,
                    tool_result=tool_result,
                )

                await websocket.send_json(
                    {
                        "type": "tool_use",
                        "tool": tool_name,
                        "result": json.loads(tool_result) if tool_result else {},
                    }
                )
            
            messages.append({
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    } for tc in tool_calls_list
                ]
            })
            
            tool_results = []
            for tool_call in tool_calls_list:
                try:
                    tool_result = await process_tool_call(
                        tool_call.function.name,
                        json.loads(tool_call.function.arguments),
                    )
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result,
                    })
                except Exception as e:
                    print(f"Error processing tool result: {e}")

            messages.extend(tool_results)
        if not has_tool_use:
            break

    await websocket.send_json({"type": "done"})

@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()

    user_id = f"user_{uuid.uuid4().hex[:8]}"
    state = ConversationState(session_id, user_id)

    try:
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "status": "active",
        }
        supabase.table("sessions").insert(session_data).execute()
        await state.add_event("session_start", content=session_id)
        messages = []

        while True:
            data = await websocket.receive_json()

            if data.get("type") == "message":
                user_input = data.get("content", "").strip()

                if not user_input:
                    continue
                await state.add_event(
                    "user_message", role="user", content=user_input
                )
                messages.append({"role": "user", "content": user_input})
                await stream_llm_response(state, messages, websocket)

    except WebSocketDisconnect:
        await handle_session_end(state, messages)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await handle_session_end(state, messages)

async def handle_session_end(state: ConversationState, messages: list):
    end_time = datetime.now(timezone.utc)
    duration = int((end_time - state.start_time).total_seconds())
    events = supabase.table("events").select("*").eq(
        "session_id", state.session_id
    ).order("sequence_num").execute()
    narrative = []
    for event in events.data:
        if event["event_type"] == "user_message":
            narrative.append(f"User: {event['content']}")
        elif event["event_type"] == "assistant_message":
            narrative.append(f"Assistant: {event['content']}")
        elif event["event_type"] == "tool_call":
            narrative.append(
                f"[Tool Call] {event['tool_name']}: {event['content']}"
            )
    conversation_text = "\n".join(narrative)
    try:
        summary_response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": f"""Summarize this conversation in bullet points. 
Keep it under 150 words. Include key topics, user intent, and assistant actions.

Conversation:
{conversation_text}"""
                }
            ],
        )

        summary = summary_response.choices[0].message.content

    except Exception as e:
        print(f"Error generating summary: {e}")
        summary = "Summary generation failed"

    await state.add_event("session_end", content=summary)
    try:
        supabase.table("sessions").update(
            {
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "summary": summary,
                "status": "completed",
            }
        ).eq("session_id", state.session_id).execute()
        print(
            f"Session {state.session_id} completed. Duration: {duration}s. Summary: {summary[:100]}..."
        )

    except Exception as e:
        print(f"Error updating session: {e}")

@app.get("/")
async def root():
    return {
        "status": "running",
        "service": "Async LLM Conversational Backend with Groq",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoints": {
            "websocket": "/ws/session/{session_id}",
            "health": "/health",
            "docs": "/docs"
        },
        "features": [
            "Real-time WebSocket streaming",
            "Groq mixtral-8x7b-32768 (Ultra-Fast)",
            "Tool calling & function execution",
            "Async database persistence (Supabase)",
            "Post-session summarization"
        ]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "connected",
        "llm": "ready"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)