from fastapi import APIRouter, HTTPException, Query
from app.schemas.planner_schema import (
    PlannerBoardCreate, PlannerBoardUpdate, PlannerBoardResponse,
    PlannerTaskCreate, PlannerTaskUpdate, PlannerTaskResponse,
)
from app.services.planner_service import (
    create_board, get_boards, update_board, delete_board,
    create_task, get_tasks, update_task, delete_task,
)
from app.services.activity_service import update_user_activity

router = APIRouter()

# ── Board (Plan) endpoints ──

@router.post("/boards", response_model=PlannerBoardResponse)
async def create_planner_board(board: PlannerBoardCreate):
    board_dict = board.model_dump()
    user_id = board_dict['userId']
    new_board = await create_board(user_id, board_dict)
    await update_user_activity(user_id, 'planner')
    return new_board

@router.get("/boards", response_model=list[PlannerBoardResponse])
async def get_planner_boards(userId: str = Query(...)):
    boards = await get_boards(userId)
    return boards

@router.put("/boards/{board_id}", response_model=PlannerBoardResponse)
async def update_planner_board(board_id: str, board: PlannerBoardUpdate, userId: str = Query(...)):
    update_data = board.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields provided")
    updated = await update_board(userId, board_id, update_data)
    return updated

@router.delete("/boards/{board_id}")
async def delete_planner_board(board_id: str, userId: str = Query(...)):
    result = await delete_board(userId, board_id)
    return result

# ── Task endpoints ──

@router.post("/tasks", response_model=PlannerTaskResponse)
async def create_planner_task(task: PlannerTaskCreate):
    task_dict = task.model_dump()
    user_id = task_dict['userId']
    new_task = await create_task(user_id, task_dict)
    await update_user_activity(user_id, 'planner')
    return new_task

@router.get("/tasks", response_model=list[PlannerTaskResponse])
async def get_planner_tasks(userId: str = Query(...), boardId: str = Query(None)):
    tasks = await get_tasks(userId, boardId)
    return tasks

@router.put("/tasks/{task_id}", response_model=PlannerTaskResponse)
async def update_planner_task(task_id: str, task: PlannerTaskUpdate, userId: str = Query(...)):
    update_data = task.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields provided")
    updated = await update_task(userId, task_id, update_data)
    return updated

@router.delete("/tasks/{task_id}")
async def delete_planner_task(task_id: str, userId: str = Query(...)):
    result = await delete_task(userId, task_id)
    return result
