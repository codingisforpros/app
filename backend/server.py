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
import requests
import redis.asyncio as redis
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Redis connection for caching
redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)

# JWT Configuration
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Metals API Configuration
METALS_API_KEY = os.environ.get('METALS_API_KEY', 'your_metals_api_key_here')
METALS_API_URL = "https://www.metals-api.com/api/gold-price-india"

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
    # SIP fields
    monthly_sip_amount: Optional[float] = 0
    sip_start_date: Optional[datetime] = None
    step_up_percentage: Optional[float] = 0
    is_sip_active: Optional[bool] = False

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

class GoldPrices(BaseModel):
    gold_22k: float
    gold_24k: float
    timestamp: datetime
    unit: str = "per gram"

class ProjectionInput(BaseModel):
    asset_class: str
    current_value: float
    annual_growth_rate: float
    annual_investment: float
    years: int

class Milestone(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    target_amount: float
    target_date: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProjectionResult(BaseModel):
    year: int
    total_value: float
    investment_added: float
    growth: float

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

# Gold Price Functions
async def get_gold_prices() -> Optional[GoldPrices]:
    """Fetch gold prices from Metals-API with caching"""
    try:
        # Check cache first
        cached_prices = await redis_client.get("gold_prices")
        if cached_prices:
            data = json.loads(cached_prices)
            return GoldPrices(**data)
        
        # Fetch from API
        if METALS_API_KEY == 'your_metals_api_key_here':
            # Return mock data for demo
            mock_prices = GoldPrices(
                gold_22k=5850.0,
                gold_24k=6350.0,
                timestamp=datetime.utcnow()
            )
            await redis_client.setex("gold_prices", 3600, mock_prices.json())
            return mock_prices
        
        params = {
            "access_key": METALS_API_KEY,
            "symbols": "VIJA-22k,VISA-24k"
        }
        
        response = requests.get(METALS_API_URL, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get("success"):
            gold_prices = GoldPrices(
                gold_22k=data["rates"]["VIJA-22k"],
                gold_24k=data["rates"]["VISA-24k"],
                timestamp=datetime.utcnow()
            )
            
            # Cache for 1 hour
            await redis_client.setex("gold_prices", 3600, gold_prices.json())
            return gold_prices
        else:
            raise Exception("API returned unsuccessful response")
            
    except Exception as e:
        logging.error(f"Error fetching gold prices: {e}")
        return None

def calculate_compound_growth(principal: float, annual_rate: float, annual_investment: float, years: int) -> List[ProjectionResult]:
    """Calculate compound growth with annual investments"""
    results = []
    current_value = principal
    
    for year in range(1, years + 1):
        # Add annual investment at the beginning of the year
        current_value += annual_investment
        
        # Apply growth rate
        growth = current_value * (annual_rate / 100)
        current_value += growth
        
        results.append(ProjectionResult(
            year=year,
            total_value=current_value,
            investment_added=annual_investment,
            growth=growth
        ))
    
    return results

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

# Gold Price endpoints
@api_router.get("/gold-prices", response_model=GoldPrices)
async def get_current_gold_prices():
    """Get current gold prices"""
    prices = await get_gold_prices()
    if not prices:
        raise HTTPException(status_code=503, detail="Gold price service unavailable")
    return prices

@api_router.post("/gold/calculate-value")
async def calculate_gold_value(weight_grams: float, purity: str = "24k"):
    """Calculate current value of gold investment"""
    prices = await get_gold_prices()
    if not prices:
        raise HTTPException(status_code=503, detail="Gold price service unavailable")
    
    rate_per_gram = prices.gold_24k if purity == "24k" else prices.gold_22k
    current_value = weight_grams * rate_per_gram
    
    return {
        "weight_grams": weight_grams,
        "purity": purity,
        "rate_per_gram": rate_per_gram,
        "current_value": current_value,
        "timestamp": prices.timestamp
    }

# Asset endpoints with auto gold calculation
@api_router.post("/assets", response_model=Asset)
async def create_asset(asset_data: AssetCreate, current_user: User = Depends(get_current_user)):
    asset = Asset(user_id=current_user.id, **asset_data.dict())
    
    # Auto-calculate current value for gold
    if asset.asset_type == AssetType.GOLD and asset.metadata.get("weight_grams"):
        try:
            prices = await get_gold_prices()
            if prices:
                weight = asset.metadata["weight_grams"]
                purity = asset.metadata.get("purity", "24k")
                rate = prices.gold_24k if purity == "24k" else prices.gold_22k
                asset.current_value = weight * rate
                asset.metadata["auto_calculated"] = True
                asset.metadata["last_price_update"] = prices.timestamp.isoformat()
        except Exception as e:
            logging.error(f"Error auto-calculating gold value: {e}")
    
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

# Milestone endpoints
@api_router.post("/milestones", response_model=Milestone)
async def create_milestone(milestone_data: dict, current_user: User = Depends(get_current_user)):
    milestone = Milestone(
        user_id=current_user.id,
        name=milestone_data["name"],
        target_amount=milestone_data["target_amount"],
        target_date=datetime.fromisoformat(milestone_data["target_date"].replace('Z', '+00:00'))
    )
    await db.milestones.insert_one(milestone.dict())
    return milestone

@api_router.get("/milestones", response_model=List[Milestone])
async def get_milestones(current_user: User = Depends(get_current_user)):
    milestones = await db.milestones.find({"user_id": current_user.id}).to_list(1000)
    return [Milestone(**milestone) for milestone in milestones]

@api_router.delete("/milestones/{milestone_id}")
async def delete_milestone(milestone_id: str, current_user: User = Depends(get_current_user)):
    result = await db.milestones.delete_one({"id": milestone_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return {"message": "Milestone deleted successfully"}

# Projection endpoints
@api_router.post("/projections/calculate")
async def calculate_projections(projections: List[ProjectionInput], current_user: User = Depends(get_current_user)):
    """Calculate net worth projections based on current assets and growth rates"""
    
    total_projections = []
    years = max(p.years for p in projections) if projections else 10
    
    # Initialize yearly totals
    yearly_totals = {year: {"total_value": 0, "total_investment": 0, "total_growth": 0} 
                    for year in range(1, years + 1)}
    
    # Calculate each asset class projection
    for projection in projections:
        asset_projections = calculate_compound_growth(
            projection.current_value,
            projection.annual_growth_rate,
            projection.annual_investment,
            projection.years
        )
        
        # Add to yearly totals
        for result in asset_projections:
            if result.year <= years:
                yearly_totals[result.year]["total_value"] += result.total_value
                yearly_totals[result.year]["total_investment"] += result.investment_added
                yearly_totals[result.year]["total_growth"] += result.growth
    
    # Convert to list format
    for year in range(1, years + 1):
        total_projections.append({
            "year": year,
            "total_value": yearly_totals[year]["total_value"],
            "investment_added": yearly_totals[year]["total_investment"],
            "growth": yearly_totals[year]["total_growth"]
        })
    
    return total_projections

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
    
    # Update gold assets with current prices
    updated_assets = []
    for asset in assets:
        asset_obj = Asset(**asset)
        if asset_obj.asset_type == AssetType.GOLD and asset_obj.metadata.get("weight_grams"):
            try:
                prices = await get_gold_prices()
                if prices:
                    weight = asset_obj.metadata["weight_grams"]
                    purity = asset_obj.metadata.get("purity", "24k")
                    rate = prices.gold_24k if purity == "24k" else prices.gold_22k
                    asset_obj.current_value = weight * rate
                    asset_obj.metadata["auto_calculated"] = True
                    asset_obj.metadata["last_price_update"] = prices.timestamp.isoformat()
                    
                    # Update in database
                    await db.assets.update_one(
                        {"id": asset_obj.id},
                        {"$set": {"current_value": asset_obj.current_value, "metadata": asset_obj.metadata}}
                    )
            except Exception as e:
                logging.error(f"Error updating gold price for asset {asset_obj.id}: {e}")
        
        updated_assets.append(asset_obj)
    
    total_investment = sum(asset.purchase_value for asset in updated_assets)
    total_net_worth = sum(asset.current_value for asset in updated_assets)
    total_gain_loss = total_net_worth - total_investment
    gain_loss_percentage = (total_gain_loss / total_investment * 100) if total_investment > 0 else 0
    
    # Calculate asset allocation
    asset_allocation = {}
    for asset in updated_assets:
        asset_type = asset.asset_type
        if asset_type not in asset_allocation:
            asset_allocation[asset_type] = 0
        asset_allocation[asset_type] += asset.current_value
    
    # Get recent assets (last 5)
    recent_assets = sorted(updated_assets, key=lambda x: x.created_at, reverse=True)[:5]
    
    return DashboardSummary(
        total_net_worth=total_net_worth,
        total_investment=total_investment,
        total_gain_loss=total_gain_loss,
        gain_loss_percentage=gain_loss_percentage,
        asset_allocation=asset_allocation,
        recent_assets=recent_assets
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
    await redis_client.close()
