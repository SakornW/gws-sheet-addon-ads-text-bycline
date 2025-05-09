from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import gws_router  # Import the new GWS router
from app.api import auth, endpoints

# from app.core.config import settings  # Commented out for now as unused

app = FastAPI(title="Ads Text Generator")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(endpoints.router, prefix="/api/v1", tags=["endpoints"])
app.include_router(gws_router.router)  # Add the GWS router


@app.get("/")
def read_root():
    return {"message": "Welcome to Ads Text Generator API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
