from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import DATA_DIR, UPLOAD_DIR, HEATMAP_DIR
from app.db.init_db import init_db
from app.api.v1.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="SSB Document Screening System",
    description="AI-Based Fake Identity & Document Screening Platform for Sashastra Seema Bal (SIH26188)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static storage directories for uploaded document scans and generated heatmaps
app.mount("/static/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/static/heatmaps", StaticFiles(directory=str(HEATMAP_DIR)), name="heatmaps")
if (DATA_DIR / "sample_documents").exists():
    app.mount("/static/sample_documents", StaticFiles(directory=str(DATA_DIR / "sample_documents")), name="sample_documents")

# Include API Router
app.include_router(api_router, prefix="/api/v1")



@app.get("/")
@app.get("/api/v1/health")
def health_check():
    return {
        "system": "SSB AI Document Screening Platform",
        "status": "ONLINE",
        "checkpoint": "Raxaul Checkpoint (Indo-Nepal Border)",
        "version": "1.0.0"
    }

