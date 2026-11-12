from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from routes.pipeline_routes import router as pipeline_router
from routes.trigger_routes import router as trigger_router
from services.storage import init_db
from services.watcher import start_watcher

# Initialize SQLite database schema
init_db()

app = FastAPI(title=settings.app_name, debug=settings.debug)
start_watcher(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline_router, prefix="/pipeline", tags=["Pipeline"])
app.include_router(trigger_router, prefix="/pipeline", tags=["Email Trigger"])



@app.get("/")
def root():
    return {"status": "ok", "app": settings.app_name, "message": "Client UI build directory not found."}