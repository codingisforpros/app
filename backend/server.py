from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import jwt
import bcrypt
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Create the main app without a prefix
app = FastAPI(title="Wealth Tracker API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Enums
class AssetType(str, Enum):
    STOCKS = "stocks"
    MUTUAL_FUNDS = "mutual_funds" 
    CRYPTOCURRENCY = "cryptocurrency"
    REAL_ESTATE = "real_estate"
    FIXED_DEPOSITS = "fixed_deposits"
    GOLD = "gold"
    OTHERS = "others"

# Models
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: EmailStr
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Token(BaseModel):
    access_token: str
    token_type: str

class AssetCreate(BaseModel):
    asset_type: AssetType
    name: str
    purchase_value: float
    current_value: float
    purchase_date: datetime
    metadata: Optional[Dict[str, Any]] = {}

class Asset(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    asset_type: AssetType
    name: str
    purchase_value: float
    current_value: float
    purchase_date: datetime
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    current_value: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class DashboardSummary(BaseModel):
    total_net_worth: float
    total_investment: float
    total_gain_loss: float
    gain_loss_percentage: float
    asset_allocation: Dict[str, float]
    recent_assets: List[Asset]

# Utility functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        user = await db.users.find_one({"id": user_id})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(**user)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

# Auth endpoints
@api_router.post("/register", response_model=Token)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = hash_password(user_data.password)
    user = User(name=user_data.name, email=user_data.email)
    user_dict = user.dict()
    user_dict["password"] = hashed_password
    
    await db.users.insert_one(user_dict)
    
    # Create token
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user["id"]})
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# Asset endpoints
@api_router.post("/assets", response_model=Asset)
async def create_asset(asset_data: AssetCreate, current_user: User = Depends(get_current_user)):
    asset = Asset(user_id=current_user.id, **asset_data.dict())
    await db.assets.insert_one(asset.dict())
    return asset

@api_router.get("/assets", response_model=List[Asset])
async def get_assets(current_user: User = Depends(get_current_user)):
    assets = await db.assets.find({"user_id": current_user.id}).to_list(1000)
    return [Asset(**asset) for asset in assets]

@api_router.get("/assets/{asset_id}", response_model=Asset)
async def get_asset(asset_id: str, current_user: User = Depends(get_current_user)):
    asset = await db.assets.find_one({"id": asset_id, "user_id": current_user.id})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return Asset(**asset)

@api_router.put("/assets/{asset_id}", response_model=Asset)
async def update_asset(asset_id: str, asset_data: AssetUpdate, current_user: User = Depends(get_current_user)):
    asset = await db.assets.find_one({"id": asset_id, "user_id": current_user.id})
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    update_data = {k: v for k, v in asset_data.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    await db.assets.update_one({"id": asset_id}, {"$set": update_data})
    
    updated_asset = await db.assets.find_one({"id": asset_id})
    return Asset(**updated_asset)

@api_router.delete("/assets/{asset_id}")
async def delete_asset(asset_id: str, current_user: User = Depends(get_current_user)):
    result = await db.assets.delete_one({"id": asset_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": "Asset deleted successfully"}

# Dashboard endpoint
@api_router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard(current_user: User = Depends(get_current_user)):
    assets = await db.assets.find({"user_id": current_user.id}).to_list(1000)
    
    if not assets:
        return DashboardSummary(
            total_net_worth=0,
            total_investment=0,
            total_gain_loss=0,
            gain_loss_percentage=0,
            asset_allocation={},
            recent_assets=[]
        )
    
    total_investment = sum(asset["purchase_value"] for asset in assets)
    total_net_worth = sum(asset["current_value"] for asset in assets)
    total_gain_loss = total_net_worth - total_investment
    gain_loss_percentage = (total_gain_loss / total_investment * 100) if total_investment > 0 else 0
    
    # Calculate asset allocation
    asset_allocation = {}
    for asset in assets:
        asset_type = asset["asset_type"]
        if asset_type not in asset_allocation:
            asset_allocation[asset_type] = 0
        asset_allocation[asset_type] += asset["current_value"]
    
    # Get recent assets (last 5)
    recent_assets = sorted(assets, key=lambda x: x["created_at"], reverse=True)[:5]
    
    return DashboardSummary(
        total_net_worth=total_net_worth,
        total_investment=total_investment,
        total_gain_loss=total_gain_loss,
        gain_loss_percentage=gain_loss_percentage,
        asset_allocation=asset_allocation,
        recent_assets=[Asset(**asset) for asset in recent_assets]
    )

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
