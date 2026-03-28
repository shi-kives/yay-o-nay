from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import os
from dotenv import load_dotenv
load_dotenv(override=True)

api_key = os.getenv("API_KEY")
if not api_key:
    raise HTTPException(status_code=500, detail="API_KEY env variable not set")

class APIKeyMiddleware(BaseHTTPMiddleware):
    EXEMPT = {"/docs", "/openapi.json","/redoc","/health"}

    async def dispatch(self, request, call_next):
        if request.url.path in self.EXEMPT:
            return await call_next(request)
        
        key = request.headers.get("X-API-Key")
        if key != api_key:
            raise HTTPException(status_code=403, detail="invalid or missing API key")
        
        return await call_next(request)