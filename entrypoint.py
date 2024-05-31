import uvicorn
from back_fastapi import main

"""
Entry point to start this application
When the entry point is different, Please consider the relative path of packages.
"""

if __name__ == "__main__":
    # uvicorn.run(main.app, host="0.0.0.0", port=8000)x
    uvicorn.run("back_fastapi.main:app", host="0.0.0.0", port=8000, reload=True)
