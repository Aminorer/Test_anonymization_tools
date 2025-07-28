from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
import os
from app.api.routes import anonymizer
from app.core.config import settings

# Create FastAPI app
app = FastAPI(
    title="Anonymiseur Juridique RGPD",
    description="Application d'anonymisation de documents juridiques 100% conforme RGPD",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Include routers
app.include_router(
    anonymizer.router,
    prefix="/api",
    tags=["anonymizer"]
)

@app.get("/")
async def root():
    return {
        "message": "Anonymiseur Juridique RGPD API",
        "version": "1.0.0",
        "status": "active",
        "rgpd_compliant": True
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.ENVIRONMENT == "development" else False
    )