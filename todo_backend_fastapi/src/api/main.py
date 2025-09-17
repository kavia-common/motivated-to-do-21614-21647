import os
from typing import List, Optional
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure OpenAPI metadata and tags
openapi_tags = [
    {"name": "Health", "description": "Service health and readiness checks."},
    {"name": "Quotes", "description": "Motivational quotes proxied from a public API."},
    {"name": "Todos", "description": "Todo CRUD endpoints (Supabase-ready)."},
    {"name": "Info", "description": "API usage and environment info."},
]

app = FastAPI(
    title="Motivated To-Do Backend API",
    description="Backend service providing health checks, a quote proxy endpoint, and Supabase-ready Todo CRUD skeletons.",
    version="0.1.0",
    openapi_tags=openapi_tags,
)

# CORS configuration: allow frontends specified via env; default to wildcard for development.
# IMPORTANT: Configure FRONTEND_ORIGINS in environment for production security.
frontend_origins_env = os.getenv("FRONTEND_ORIGINS", "*")
if frontend_origins_env.strip() == "*":
    allow_origins: List[str] = ["*"]
else:
    allow_origins = [o.strip() for o in frontend_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Models
# -----------------------------

class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall health status indicator.")
    service: str = Field(..., description="Service name.")
    version: str = Field(..., description="API version.")


class QuoteResponse(BaseModel):
    quote: str = Field(..., description="Motivational quote text.")
    author: Optional[str] = Field(None, description="Author of the quote, if available.")
    source: str = Field(..., description="The upstream API or provider.")


class TodoBase(BaseModel):
    title: str = Field(..., description="Short title of the todo.")
    completed: bool = Field(False, description="Completion state of the todo.")


class TodoCreate(TodoBase):
    pass


class TodoUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Updated title.")
    completed: Optional[bool] = Field(None, description="Updated completion state.")


class Todo(TodoBase):
    id: UUID = Field(..., description="Unique identifier for the todo.")
    user_id: Optional[str] = Field(None, description="Owner user ID (from Supabase auth).")


# In-memory store for dev/demo only (replace with Supabase)
IN_MEMORY_TODOS: dict[UUID, Todo] = {}


# -----------------------------
# Routes
# -----------------------------

# PUBLIC_INTERFACE
@app.get("/health", response_model=HealthResponse, tags=["Health"], summary="Health Check", description="Returns the health status of the backend service.")
def health_check() -> HealthResponse:
    """This endpoint returns a simple health status response.

    Returns:
        HealthResponse: Object containing status, service name, and API version.
    """
    return HealthResponse(status="ok", service="todo_backend_fastapi", version=app.version)


# PUBLIC_INTERFACE
@app.get(
    "/quote",
    response_model=QuoteResponse,
    tags=["Quotes"],
    summary="Get a motivational quote",
    description="Proxies a motivational quote from a public API and returns it to the client.",
    responses={
        200: {"description": "Quote fetched successfully"},
        502: {"description": "Bad gateway - upstream quote service failed"},
    },
)
async def get_quote() -> QuoteResponse:
    """Fetch a motivational quote from an external public API.

    Returns:
        QuoteResponse: A quote and metadata from the upstream provider.
    """
    # Primary API: type.fit free quotes API (static list but widely used)
    # Fallback API: zenquotes.io
    # You may adjust these as needed if rate limits occur.
    providers = [
        {
            "name": "type.fit",
            "url": "https://type.fit/api/quotes",
            "transform": lambda data: (
                (data[0].get("text", "").strip(), (data[0].get("author") or "").strip())
                if isinstance(data, list) and data
                else ("Keep pushing forward.", "Unknown")
            ),
        },
        {
            "name": "zenquotes.io",
            "url": "https://zenquotes.io/api/random",
            "transform": lambda data: (
                (data[0].get("q", "").strip(), data[0].get("a", "").strip())
                if isinstance(data, list) and data
                else ("Believe you can and you're halfway there.", "Theodore Roosevelt")
            ),
        },
    ]

    async with httpx.AsyncClient(timeout=10) as client:
        last_error = None
        for p in providers:
            try:
                resp = await client.get(p["url"])
                resp.raise_for_status()
                data = resp.json()
                quote_text, author = p["transform"](data)
                if not quote_text:
                    continue
                return QuoteResponse(quote=quote_text, author=author or None, source=p["name"])
            except Exception as e:
                last_error = e
                continue

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Failed to fetch quote from upstream providers: {last_error}",
    )


# -----------------------------
# Todo CRUD - Supabase-ready skeletons
# For now these use an in-memory store. Replace with Supabase integration by:
#  - Validating auth via Supabase JWT (Authorization: Bearer <token>)
#  - Using Supabase Python client or REST to persist rows in a 'todos' table
#  - Filtering todos by user_id (row-level security recommended)
# -----------------------------

# PUBLIC_INTERFACE
@app.get(
    "/todos",
    response_model=List[Todo],
    tags=["Todos"],
    summary="List todos",
    description="List all todos for the current user. For demo, returns all in-memory todos. Replace with Supabase query filtered by user_id.",
)
def list_todos(user_id: Optional[str] = Query(None, description="User ID to filter todos; in production derive from auth token")) -> List[Todo]:
    """List todos. In production, use Supabase with RLS, filtering by the authenticated user's ID."""
    if user_id:
        return [t for t in IN_MEMORY_TODOS.values() if t.user_id == user_id]
    return list(IN_MEMORY_TODOS.values())


# PUBLIC_INTERFACE
@app.post(
    "/todos",
    response_model=Todo,
    tags=["Todos"],
    status_code=status.HTTP_201_CREATED,
    summary="Create a todo",
    description="Create a new todo item. In production, insert into Supabase and associate with the authenticated user's ID.",
)
def create_todo(todo: TodoCreate, user_id: Optional[str] = Query(None, description="User ID owner; in production derive from auth token")) -> Todo:
    """Create a todo. Replace with Supabase insert and return inserted row."""
    # Use keyword arguments; the previous version had a positional arg after keyword causing a SyntaxError.
    new_todo = Todo(id=uuid4(), title=todo.title, completed=todo.completed, user_id=user_id)
    IN_MEMORY_TODOS[new_todo.id] = new_todo
    return new_todo


# PUBLIC_INTERFACE
@app.patch(
    "/todos/{todo_id}",
    response_model=Todo,
    tags=["Todos"],
    summary="Update a todo",
    description="Update fields of a todo item. In production, update row in Supabase with RLS checks.",
)
def update_todo(todo_id: UUID, patch: TodoUpdate) -> Todo:
    """Update a todo by ID. Replace with Supabase update and return updated row."""
    existing = IN_MEMORY_TODOS.get(todo_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    update_data = existing.model_dump()
    if patch.title is not None:
        update_data["title"] = patch.title
    if patch.completed is not None:
        update_data["completed"] = patch.completed
    updated = Todo(**update_data)
    IN_MEMORY_TODOS[todo_id] = updated
    return updated


# PUBLIC_INTERFACE
@app.delete(
    "/todos/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Todos"],
    summary="Delete a todo",
    description="Delete a todo item by ID. In production, delete row in Supabase with RLS checks.",
)
def delete_todo(todo_id: UUID) -> None:
    """Delete a todo by ID. Replace with Supabase delete."""
    if todo_id not in IN_MEMORY_TODOS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    del IN_MEMORY_TODOS[todo_id]
    return None


# PUBLIC_INTERFACE
@app.get(
    "/",
    tags=["Info"],
    summary="Root info",
    description="Basic info endpoint. Use /health for health checks.",
)
def root_info():
    """Root endpoint providing basic service info."""
    return {"message": "Motivated To-Do Backend", "health": "/health", "quote": "/quote", "todos": "/todos"}
