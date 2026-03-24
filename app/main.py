from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, admin, ai, news, planner, weather

app = FastAPI(title="Atmos Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.services.firebase_service import init_firebase

@app.on_event("startup")
async def startup_event():
    init_firebase()

from fastapi.responses import JSONResponse
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"Unhandled exception: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)},
        headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Credentials": "true"}
    )


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(news.router, prefix="/api/news", tags=["news"])
app.include_router(planner.router, prefix="/api/planner", tags=["planner"])
app.include_router(weather.router, prefix="/api/weather", tags=["weather"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Atmos Backend"}
