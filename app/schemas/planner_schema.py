from pydantic import BaseModel, Field
from typing import Optional

# ── Plan Board (top-level container) ──
class PlannerBoardBase(BaseModel):
    name: str
    description: Optional[str] = ""

class PlannerBoardCreate(PlannerBoardBase):
    userId: str

class PlannerBoardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class PlannerBoardResponse(PlannerBoardBase):
    id: str
    task_count: int = 0

    class Config:
        from_attributes = True

# ── Task (belongs to a board) ──
class PlannerTaskBase(BaseModel):
    title: str
    description: Optional[str] = ""
    status: str = Field("todo", description="One of: todo, in_progress, done")
    weather_condition_target: Optional[str] = None
    due_date: Optional[str] = None  # ISO format string, optional

class PlannerTaskCreate(PlannerTaskBase):
    userId: str
    board_id: str

class PlannerTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    weather_condition_target: Optional[str] = None
    due_date: Optional[str] = None

class PlannerTaskResponse(PlannerTaskBase):
    id: str
    board_id: Optional[str] = None

    class Config:
        from_attributes = True
