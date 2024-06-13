import uvicorn
import os
import sys
import logging.config
from datetime import timedelta  
"""Debugging Setting"""

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger("Fast API in Sceh-Zoom")
# Set logger name to project
logger.info("START Application")



from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from routers import register, login


# Define Fast api and description
app = FastAPI(
    title="Fast API in Sceh-Zoom",
    description="Fast API in Sceh-Zoom",
    version="0.0.1",
)






# This path is for health check or test
@app.get("/")
async def root():
    return {"Connect FU"}


# 각 라우터를 애플리케이션에 등록
app.include_router(register.router, prefix="/register", tags=["register"])
app.include_router(login.router, prefix="/login", tags=["login"])