from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

app = FastAPI()

# Templates setup
templates = Jinja2Templates(directory="templates")

# Fake Database
users_db = {}

class UserSignup(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(user: UserSignup):
    if user.email in users_db:
        raise HTTPException(status_code=400, detail="Email pehle se register hai")
    
    user_id = len(users_db) + 1
    users_db[user.email] = {
        "id": user_id,
        "username": user.username,
        "email": user.email,
        "password": user.password
    }
    return {"id": user_id, "username": user.username, "email": user.email}

@app.post("/login")
async def login(user: UserLogin):
    if user.email not in users_db or users_db[user.email]["password"] != user.password:
        raise HTTPException(status_code=401, detail="Galat Email ya Password")
    
    return {
        "access_token": f"fake-access-token-for-{users_db[user.email]['username']}",
        "refresh_token": f"fake-refresh-token-for-{users_db[user.email]['username']}",
        "token_type": "bearer"
    }