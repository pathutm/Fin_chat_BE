from fastapi import FastAPI

from schemas.chat import ChatRequest, ChatResponse
from services.chat import handle_chat_logic


app = FastAPI(title="Finance AI Chatbot")


@app.get("/")
def home():
    return {
        "message": "Finance AI Chatbot is running"
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):

    final_response, generated_agent = await handle_chat_logic(
        request.message,
        request.conversation_id,
        user_name=request.user_name,
        user_id=request.user_id
    )

    return ChatResponse(
        response=final_response,
        agent=generated_agent
    )