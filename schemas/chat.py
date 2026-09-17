from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    conversation_id: str
    user_name: str | None = None
    user_id: str | None = None

class ChatResponse(BaseModel):
    response: str
    agent: str
