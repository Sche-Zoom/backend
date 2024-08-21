import uvicorn
import os
import sys
import logging.config
from datetime import timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger("Fast API in rich_schedule")
logger.info("START Application")

from fastapi import FastAPI, Security, HTTPException, status, APIRouter, Query
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from routers import register, login, per_schedule
from typing import List, Optional

app = FastAPI(
    title="Fast API in rich_schedule",
    description="Fast API in rich_schedule",
    version="0.0.1",
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Define the root endpoint
@app.get("/")
async def some_method():
    return {"message": "OK"}

# 각 라우터를 애플리케이션에 등록
app.include_router(register.router, prefix="/api/sign/register", tags=["register"])
app.include_router(login.router, prefix="/api/sign/login", tags=["login"])
app.include_router(per_schedule.router, prefix="/api/per-schedule")


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)