import os
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

app = FastAPI(title="Falcone's Pizza Inventory")

# --- Settings ---
WEB_DIR = Path("web")
FLAGS_DIR = Path("global_flags")
NO_AUTH_FILE = FLAGS_DIR / "no_auth"

# Setup directories
WEB_DIR.mkdir(exist_ok=True)
FLAGS_DIR.mkdir(exist_ok=True)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Mock Data ---
MOCK_USERS = {
    "kitchen": "1234",
    "manager": "4321"
}

# --- Models ---
class LoginRequest(BaseModel):
    username: str
    pin: str

# --- Dependencies ---
def is_auth_enabled() -> bool:
    return not NO_AUTH_FILE.exists()

# --- API Endpoints ---
@app.get("/api/status")
async def get_status():
    return {"auth_required": is_auth_enabled(), "status": "online"}

@app.post("/api/login")
async def login(request: LoginRequest):
    if not is_auth_enabled():
         return {"success": True, "message": "Auth disabled", "user": request.username or "anonymous"}

    user = request.username.lower()
    if user in MOCK_USERS and MOCK_USERS[user] == request.pin:
        return {"success": True, "message": "Login successful", "user": user}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or PIN",
    )

# Placeholder data endpoint
@app.get("/api/inventory/{category}")
async def get_inventory(category: str):
    # Dummy data
    data = {
        "produce": [
            {"id": "p1", "name": "Tomatoes", "qty": 10, "unit": "cases", "par": 15},
            {"id": "p2", "name": "Onions", "qty": 5, "unit": "bags", "par": 10},
            {"id": "p3", "name": "Garlic", "qty": 2, "unit": "lbs", "par": 5},
        ],
        "meat": [
            {"id": "m1", "name": "Pepperoni", "qty": 8, "unit": "cases", "par": 10},
            {"id": "m2", "name": "Sausage", "qty": 4, "unit": "cases", "par": 8},
        ],
        "dairy": [
            {"id": "d1", "name": "Mozzarella", "qty": 20, "unit": "blocks", "par": 25},
            {"id": "d2", "name": "Parmesan", "qty": 5, "unit": "tubs", "par": 6},
        ],
        "beverages": [
            {"id": "b1", "name": "Coke", "qty": 12, "unit": "cases", "par": 15},
            {"id": "b2", "name": "Sprite", "qty": 8, "unit": "cases", "par": 10},
        ]
    }

    category_lower = category.lower()
    if category_lower in data:
        return {"success": True, "items": data[category_lower]}

    return {"success": True, "items": []} # empty if not found

# --- Static Files ---
app.mount("/", StaticFiles(directory="web", html=True), name="web")

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
