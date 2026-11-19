"""
BreakGlass Guardian - Main FastAPI Application
AI-Powered Emergency AWS Access Management
"""
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from datetime import datetime

from backend.config import settings
from backend.api import requests, approvals, sessions, audit
from backend.security.auth import decode_bearer_token
from pydantic import BaseModel, Field
from jose import jwt
from datetime import timedelta

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


@app.middleware("http")
async def authentication_middleware(request: Request, call_next):
    """Authenticate API requests when production authentication is enabled."""
    if (
        (settings.auth_enabled or not settings.use_local_mode)
        and request.url.path.startswith("/api/")
        and request.url.path != "/api/auth/dev-token"
    ):
        request.state.principal = decode_bearer_token(request)
    response = await call_next(request)
    return response

# Include routers
app.include_router(requests.router, prefix="/api/requests", tags=["Requests"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["Approvals"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])


class DevelopmentIdentity(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    roles: list[str] = Field(default_factory=lambda: ["requester"])


@app.post("/api/auth/dev-token", include_in_schema=False)
async def create_development_token(identity: DevelopmentIdentity, request: Request):
    """Create a short-lived local dashboard token for development only."""
    client_host = request.client.host if request.client else ""
    if not settings.debug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if client_host not in {"127.0.0.1", "::1", "localhost"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Development login is loopback-only")

    allowed_roles = {"requester", "internal", "approver", "admin"}
    roles = [role for role in identity.roles if role in allowed_roles]
    if not roles:
        roles = ["requester"]
    if "@" not in identity.email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Valid email required")

    expires = datetime.utcnow() + timedelta(minutes=settings.auth_token_expiration_minutes)
    token = jwt.encode(
        {
            "sub": identity.email.lower().strip(),
            "roles": roles,
            "exp": expires,
        },
        settings.auth_secret_key,
        algorithm=settings.auth_algorithm,
    )
    return {"access_token": token, "token_type": "Bearer", "expires_at": expires.isoformat()}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.error(f"Validation error: {exc.errors()}")
    details = []
    for error in exc.errors():
        safe_error = dict(error)
        context = safe_error.get("ctx")
        if context:
            safe_error["ctx"] = {
                key: str(value) for key, value in context.items()
            }
        details.append(safe_error)
    suspicious = any(
        "suspicious content" in str(error.get("msg", "")).lower()
        for error in details
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST if suspicious else status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": "Request contains suspicious content and was rejected"
            if suspicious else "Request validation failed",
            "details": details
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
            "database": "local" if settings.use_local_mode else "configured",
            "bedrock_agent": "disabled" if not settings.bedrock_enabled else "configured",
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
