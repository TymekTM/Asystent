#!/usr/bin/env python3
"""Minimal test server to debug CPU usage."""

import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Minimal Test Server")

@app.get("/")
async def root():
    return {"message": "Minimal server running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="warning",
        access_log=False,
        reload=False,
    )
