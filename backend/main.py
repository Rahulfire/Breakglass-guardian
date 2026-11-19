"""
BreakGlass Guardian - Main FastAPI Application
AI-Powered Emergency AWS Access Management
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from datetime import datetime

from backend.config import settings
from backend.api import requests, approvals, sessions, audit

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="BreakGlass Guardian",
    description="AI-Powered Emergency AWS Access Management System",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(requests.router, prefix="/api/requests", tags=["Requests"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["Approvals"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "details": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "BreakGlass Guardian",
        "version": "1.0.0",
        "description": "AI-Powered Emergency AWS Access Management",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "api": "ok",
            "database": "ok",  # In production: check DynamoDB
            "bedrock_agent": "ok"  # In production: check Bedrock
        }
    }


@app.get("/api/stats")
async def get_statistics():
    """Get dashboard statistics"""
    # This will be implemented with actual data
    from backend.models.access_request import RequestStatistics
    
    return RequestStatistics(
        total_requests=0,
        approved_requests=0,
        rejected_requests=0,
        pending_approvals=0,
        active_sessions=0,
        expired_sessions=0,
        high_risk_requests=0,
        critical_risk_requests=0,
        prompt_injection_attempts=0
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
