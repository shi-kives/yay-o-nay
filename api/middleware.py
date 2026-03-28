from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import os

class APIKeyMiddleware(BaseHTTPMiddleware):
    EXEMPT = {"/docs", "/openapi.json","/redoc","/health"}

    async def dispatch(self, request, call_next):
        if request.url.path in self.EXEMPT:
            return await call_next(request)
        
        key = request.headers.get("X-API-Key")
        if key != os.getenv("API_KEY"):
            raise HTTPException(status_code=403, detail="invalid or missing API key")
        
        return await call_next(request)