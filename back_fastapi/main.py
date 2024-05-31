from fastapi import FastAPI, Depends

import logging.config
from fastapi.responses import JSONResponse
from .database import db_conn


"""Debugging Setting"""
import uvicorn


logger = logging.getLogger("Fast API in Sceh-Zoom")
# Set logger name to project
logger.info("START Application")




# Define Fast api and description
app = FastAPI(
    title="Fast API in Sceh-Zoom",
    description="Fast API in Sceh-Zoom",
    version="0.0.1",
)



db = db_conn.Database()



# This path is for health check or test
@app.get("/")
async def root():
    connection =  db.get_connection()
    return {"Connect FU"}




    
    
    
    
    
# app.include_router(register.router, prefix="/sign/register", tags=["register"])
# app.include_router(grammar_state.router, prefix="/grammar_state", tags=["grammar_state"])
# app.include_router(word_collection.router, prefix="/word_collection", tags=["word_collection"])