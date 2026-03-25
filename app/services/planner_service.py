from app.services.firebase_service import get_db
from fastapi import HTTPException
from firebase_admin import firestore

# ════════════════════════════════════════════
# BOARD (Plan) CRUD
# ════════════════════════════════════════════

async def create_board(user_id: str, board_data: dict) -> dict:
    try:
        db_client = get_db()
        board_ref = db_client.collection('users').document(user_id).collection('planner_boards').document()
        board_dict = board_data.copy()
        if 'userId' in board_dict:
            del board_dict['userId']
        board_dict['created_at'] = firestore.SERVER_TIMESTAMP
        board_ref.set(board_dict)
        board_dict['id'] = board_ref.id
        board_dict.pop('created_at', None)
        board_dict['task_count'] = 0
        return board_dict
    except Exception as e:
        print(f"Error creating board: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create plan")

async def get_boards(user_id: str) -> list:
    try:
        db_client = get_db()
        boards_ref = db_client.collection('users').document(user_id).collection('planner_boards')
        docs = boards_ref.stream()

        # Pre-fetch all tasks to count per board efficiently
        all_tasks = list(db_client.collection('users').document(user_id).collection('planner_tasks').stream())

        boards = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            data.pop('created_at', None)
            # Count tasks belonging to this board
            data['task_count'] = sum(1 for t in all_tasks if t.to_dict().get('board_id') == doc.id)
            boards.append(data)
        return boards
    except Exception as e:
        print(f"Error getting boards: {str(e)}")
        return []

async def update_board(user_id: str, board_id: str, update_data: dict) -> dict:
    try:
        db_client = get_db()
        board_ref = db_client.collection('users').document(user_id).collection('planner_boards').document(board_id)
        doc = board_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Plan not found")
        board_ref.update(update_data)
        updated_doc = board_ref.get()
        data = updated_doc.to_dict()
        data['id'] = updated_doc.id
        data.pop('created_at', None)
        data['task_count'] = 0
        return data
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error updating board: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update plan")

async def delete_board(user_id: str, board_id: str) -> dict:
    try:
        db_client = get_db()
        board_ref = db_client.collection('users').document(user_id).collection('planner_boards').document(board_id)
        doc = board_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Also delete all tasks belonging to this board
        tasks_ref = db_client.collection('users').document(user_id).collection('planner_tasks')
        task_query = tasks_ref.where("board_id", "==", board_id)
        task_docs = task_query.stream()
        batch = db_client.batch()
        count = 0
        for task_doc in task_docs:
            batch.delete(task_doc.reference)
            count += 1
            if count >= 400:
                batch.commit()
                batch = db_client.batch()
                count = 0
        if count > 0:
            batch.commit()

        board_ref.delete()
        return {"success": True, "message": "Plan deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error deleting board: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete plan")


# ════════════════════════════════════════════
# TASK CRUD (scoped to a board)
# ════════════════════════════════════════════

async def create_task(user_id: str, task_data: dict) -> dict:
    try:
        db_client = get_db()
        task_ref = db_client.collection('users').document(user_id).collection('planner_tasks').document()
        task_dict = task_data.copy()
        if 'userId' in task_dict:
            del task_dict['userId']
        task_dict['created_at'] = firestore.SERVER_TIMESTAMP
        task_ref.set(task_dict)
        task_dict['id'] = task_ref.id
        task_dict.pop('created_at', None)
        return task_dict
    except Exception as e:
        print(f"Error creating task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create task")

async def get_tasks(user_id: str, board_id: str = None) -> list:
    try:
        db_client = get_db()
        tasks_ref = db_client.collection('users').document(user_id).collection('planner_tasks')
        
        # Avoid composite index requirement — fetch all, filter in Python
        docs = tasks_ref.stream()

        tasks = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            
            # Filter by board_id in Python if specified
            if board_id and data.get('board_id') != board_id:
                continue
                
            data.pop('created_at', None)
            tasks.append(data)
        return tasks
    except Exception as e:
        print(f"Error getting tasks: {str(e)}")
        return []

async def update_task(user_id: str, task_id: str, update_data: dict) -> dict:
    try:
        db_client = get_db()
        task_ref = db_client.collection('users').document(user_id).collection('planner_tasks').document(task_id)
        doc = task_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Task not found")
        task_ref.update(update_data)
        updated_doc = task_ref.get()
        data = updated_doc.to_dict()
        data['id'] = updated_doc.id
        data.pop('created_at', None)
        return data
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error updating task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update task")

async def delete_task(user_id: str, task_id: str) -> dict:
    try:
        db_client = get_db()
        task_ref = db_client.collection('users').document(user_id).collection('planner_tasks').document(task_id)
        doc = task_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Task not found")
        task_ref.delete()
        return {"success": True, "message": "Task deleted successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error deleting task: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete task")
