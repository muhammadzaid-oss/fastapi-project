import time
from datetime import datetime, timezone
from typing import Dict, Set
import jwt
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr

app = FastAPI(title="Advanced Asynchronous Backend System (Enterprise Core)")

# --- CRYPTOGRAPHIC CONFIGURATION ---
ACCESS_SECRET = "super_secure_access_cryptographic_key_998877"
REFRESH_SECRET = "completely_different_refresh_cryptographic_key_112233"
ALGORITHM = "HS256"

# --- IN-MEMORY DATABASE & STATE LAYERS ---
fake_users_db: Dict[str, dict] = {}
user_id_counter = 1
token_blacklist: Set[str] = set()

security_scheme = HTTPBearer()


# --- HTML FRONTEND SCREEN (Dark Theme UI) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Zero-Trust Auth Interface</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #1e1e2e; color: #cdd6f4; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background-color: #313244; padding: 30px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.3); width: 380px; text-align: center; }
        h2 { color: #89b4fa; margin-bottom: 20px; }
        input { width: 90%; padding: 12px; margin: 10px 0; border-radius: 6px; border: 1px solid #45475a; background-color: #1e1e2e; color: #fff; font-size: 14px; }
        button { width: 96%; padding: 12px; background-color: #89b4fa; border: none; border-radius: 6px; color: #11111b; font-weight: bold; font-size: 16px; cursor: pointer; margin-top: 15px; transition: 0.2s; }
        button:hover { background-color: #b4befe; }
        .toggle-link { margin-top: 15px; font-size: 14px; color: #a6adc8; }
        .toggle-link a { color: #f5c2e7; text-decoration: none; font-weight: bold; }
        .status-box { margin-top: 20px; padding: 10px; background-color: #181825; border-radius: 6px; font-size: 12px; text-align: left; word-break: break-all; max-height: 120px; overflow-y: auto; display: none; }
    </style>
</head>
<body>

<div class="container">
    <h2 id="form-title">Create Account (Signup)</h2>
    
    <input type="text" id="username" placeholder="Enter Username">
    <input type="email" id="email" placeholder="Enter Email Address">
    <input type="password" id="password" placeholder="Enter Password">
    
    <button onclick="submitForm()" id="submit-btn">Register Now</button>
    
    <div class="toggle-link" id="toggle-text">
        Pehle se account hai? <a href="#" onclick="switchMode(true)">Log In Karein</a>
    </div>

    <div class="status-box" id="status-box"></div>
</div>

<script>
    let isLoginMode = false;
    let savedAccessToken = "";
    let savedRefreshToken = "";

    function switchMode(toLogin) {
        isLoginMode = toLogin;
        const title = document.getElementById('form-title');
        const usernameInput = document.getElementById('username');
        const btn = document.getElementById('submit-btn');
        const toggleText = document.getElementById('toggle-text');

        if (isLoginMode) {
            title.innerText = "Welcome Back (Login)";
            usernameInput.style.display = "none";
            btn.innerText = "Log In";
            toggleText.innerHTML = "Naya account banana hai? <a href='#' onclick='switchMode(false)'>Sign Up Karein</a>";
        } else {
            title.innerText = "Create Account (Signup)";
            usernameInput.style.display = "block";
            btn.innerText = "Register Now";
            toggleText.innerHTML = "Pehle se account hai? <a href='#' onclick='switchMode(true)'>Log In Karein</a>";
        }
    }

    async function submitForm() {
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const statusBox = document.getElementById('status-box');
        
        if (!isLoginMode) {
            const username = document.getElementById('username').value;
            const res = await fetch('/signup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password })
            });
            const data = await res.json();
            if (res.status === 201) {
                alert("Signup Kamyab! Ab login karein.");
                switchMode(true);
            } else {
                alert("Error: " + (data.detail || "Signup fail ho gaya"));
            }
        } else {
            const res = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();
            if (res.status === 200) {
                savedAccessToken = data.access_token;
                savedRefreshToken = data.refresh_token;
                alert("Login Kamyab! Tokens received perfectly.");
                
                statusBox.style.display = "block";
                statusBox.innerHTML = `<b>Access Token:</b><br>${savedAccessToken}<br><br><b>Refresh Token:</b><br>${savedRefreshToken}`;
            } else {
                alert("Error: " + (data.detail || "Login fail"));
            }
        }
    }
</script>

</body>
</html>
"""


# --- 3. RESULT SCHEMAS & OUTPUT STRUCTURES ---

class UserRegistrationResponse(BaseModel):
    id: int
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False
    created_at: str

class TokenExchangeResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserProfileResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    status: str = "Verified Active"

class StandardActionResponse(BaseModel):
    detail: str

class UserRegisterInput(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLoginInput(BaseModel):
    email: EmailStr
    password: str

class TokenRefreshInput(BaseModel):
    refresh_token: str


# --- HELPER FUNCTIONS FOR TOKENS ---
def create_jwt_token(email: str, token_type: str, expires_in_seconds: int) -> str:
    secret = ACCESS_SECRET if token_type == "access" else REFRESH_SECRET
    payload = {
        "sub": email,
        "type": token_type,
        "exp": time.time() + expires_in_seconds
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


# --- DEPENDENCY INJECTION (ZERO-TRUST SECURITY PROTECTION) ---
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)) -> str:
    token = credentials.credentials
    if token in token_blacklist:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token blacklisted.")
    try:
        payload = jwt.decode(token, ACCESS_SECRET, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type.")
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials.")


# --- SYSTEM ENDPOINTS ---

# FRONTEND DISPATCH ROUTE (UI Page open)
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    return HTML_TEMPLATE

@app.post("/signup", response_model=UserRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def signup(user: UserRegisterInput):
    global user_id_counter
    if user.email in fake_users_db:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email pehle se register hai!")
    
    dummy_secure_hash = f"sha256_fake_hash_{user.password}"
    new_user = {
        "id": user_id_counter,
        "email": user.email,
        "username": user.username,
        "password": dummy_secure_hash,
        "is_active": True,
        "is_superuser": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    fake_users_db[user.email] = new_user
    user_id_counter += 1
    return UserRegistrationResponse(
        id=new_user["id"],
        email=new_user["email"],
        is_active=new_user["is_active"],
        is_superuser=new_user["is_superuser"],
        created_at=new_user["created_at"]
    )

@app.post("/login", response_model=TokenExchangeResponse)
async def login(user: UserLoginInput):
    if user.email not in fake_users_db:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Galt email ya password!")
    db_user = fake_users_db[user.email]
    incoming_hash = f"sha256_fake_hash_{user.password}"
    if incoming_hash != db_user["password"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Galt email ya password!")
    
    access_token = create_jwt_token(user.email, token_type="access", expires_in_seconds=900) 
    refresh_token = create_jwt_token(user.email, token_type="refresh", expires_in_seconds=604800)
    return TokenExchangeResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

@app.get("/profile", response_model=UserProfileResponse)
async def get_profile(current_user: str = Depends(get_current_user)):
    user_data = fake_users_db[current_user]
    return UserProfileResponse(
        id=user_data["id"],
        username=user_data["username"],
        email=user_data["email"],
        status="Verified Active"
    )

@app.post("/refresh", response_model=TokenExchangeResponse)
async def refresh_tokens(data: TokenRefreshInput):
    try:
        payload = jwt.decode(data.refresh_token, REFRESH_SECRET, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type.")
        email = payload["sub"]
        if email not in fake_users_db:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
        new_access = create_jwt_token(email, token_type="access", expires_in_seconds=900)
        new_refresh = create_jwt_token(email, token_type="refresh", expires_in_seconds=604800)
        return TokenExchangeResponse(access_token=new_access, refresh_token=new_refresh, token_type="bearer")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.")

@app.post("/logout", response_model=StandardActionResponse)
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    token = credentials.credentials
    if token in token_blacklist:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is already invalidated.")
    
    token_blacklist.add(token)
    return StandardActionResponse(detail="Revocation complete")