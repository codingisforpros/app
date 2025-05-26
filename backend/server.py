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
import numpy as np
from scipy import stats
import pandas as pd
from datetime import datetime, timedelta, date
import calendar

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
    # SIP fields
    monthly_sip_amount: float = 0
    sip_start_date: Optional[datetime] = None
    step_up_percentage: float = 0
    is_sip_active: bool = False

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    current_value: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    # SIP fields
    monthly_sip_amount: Optional[float] = None
    step_up_percentage: Optional[float] = None
    is_sip_active: Optional[bool] = None

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
    # SIP fields
    monthly_sip_amount: float = 0
    step_up_percentage: float = 0

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
    sip_contribution: float = 0
    lumpsum_contribution: float = 0

class MonteCarloResult(BaseModel):
    percentile_10: List[float]
    percentile_25: List[float]
    percentile_50: List[float]  # Median
    percentile_75: List[float]
    percentile_90: List[float]
    years: List[int]
    confidence_range: str
    final_values: Dict[str, float]

class FinancialHealthScore(BaseModel):
    overall_score: int  # 0-1000
    category_scores: Dict[str, int]
    recommendations: List[str]
    strengths: List[str]
    areas_for_improvement: List[str]

class PerformanceAttribution(BaseModel):
    asset_contributions: Dict[str, float]
    sector_analysis: Dict[str, Dict[str, float]]
    time_weighted_returns: Dict[str, float]
    best_performers: List[Dict[str, Any]]
    worst_performers: List[Dict[str, Any]]
    correlation_matrix: Dict[str, Dict[str, float]]

class TaxOptimization(BaseModel):
    current_year_tax: Dict[str, float]
    ltcg_liability: float
    stcg_liability: float
    tax_saving_opportunities: List[Dict[str, Any]]
    harvesting_suggestions: List[Dict[str, Any]]
    total_tax_liability: float
    effective_tax_rate: float

class ExpenseCategory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    category: str
    amount: float
    date: datetime
    description: str
    is_recurring: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class IncomeEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    source: str
    amount: float
    date: datetime
    description: str
    is_recurring: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

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

# ASSET_TYPES dictionary for reference
ASSET_TYPES_DICT = {
    "stocks": "Stocks",
    "mutual_funds": "Mutual Funds", 
    "cryptocurrency": "Cryptocurrency",
    "real_estate": "Real Estate",
    "fixed_deposits": "Fixed Deposits",
    "gold": "Gold",
    "others": "Others"
}

# Advanced Analytics Functions
def run_monte_carlo_simulation(initial_value: float, annual_return: float, volatility: float, 
                              annual_investment: float, years: int, simulations: int = 10000) -> MonteCarloResult:
    """Run Monte Carlo simulation for wealth projections"""
    np.random.seed(42)  # For reproducible results
    
    results = []
    
    for _ in range(simulations):
        portfolio_value = initial_value
        yearly_values = [portfolio_value]
        
        for year in range(years):
            # Add annual investment
            portfolio_value += annual_investment
            
            # Generate random return based on normal distribution
            annual_return_this_year = np.random.normal(annual_return, volatility)
            
            # Apply return
            portfolio_value *= (1 + annual_return_this_year / 100)
            yearly_values.append(portfolio_value)
        
        results.append(yearly_values[1:])  # Exclude initial value
    
    # Calculate percentiles for each year
    results_array = np.array(results)
    
    percentile_10 = np.percentile(results_array, 10, axis=0).tolist()
    percentile_25 = np.percentile(results_array, 25, axis=0).tolist()
    percentile_50 = np.percentile(results_array, 50, axis=0).tolist()
    percentile_75 = np.percentile(results_array, 75, axis=0).tolist()
    percentile_90 = np.percentile(results_array, 90, axis=0).tolist()
    
    final_values = {
        "worst_case": float(percentile_10[-1]),
        "pessimistic": float(percentile_25[-1]),
        "most_likely": float(percentile_50[-1]),
        "optimistic": float(percentile_75[-1]),
        "best_case": float(percentile_90[-1])
    }
    
    return MonteCarloResult(
        percentile_10=percentile_10,
        percentile_25=percentile_25,
        percentile_50=percentile_50,
        percentile_75=percentile_75,
        percentile_90=percentile_90,
        years=list(range(1, years + 1)),
        confidence_range="80% (10th to 90th percentile)",
        final_values=final_values
    )

def calculate_financial_health_score(assets: List[Asset], dashboard: DashboardSummary) -> FinancialHealthScore:
    """Calculate comprehensive financial health score (0-1000)"""
    
    scores = {}
    recommendations = []
    strengths = []
    areas_for_improvement = []
    
    # 1. Portfolio Diversification (0-200 points)
    if dashboard.asset_allocation:
        asset_count = len(dashboard.asset_allocation)
        max_allocation = max(dashboard.asset_allocation.values()) / dashboard.total_net_worth * 100
        
        diversification_score = min(200, (asset_count * 30) + (100 - max_allocation) * 2)
        scores["diversification"] = int(diversification_score)
        
        if max_allocation > 70:
            areas_for_improvement.append("Portfolio is heavily concentrated in one asset class")
            recommendations.append("Consider diversifying across more asset classes")
        else:
            strengths.append("Well-diversified portfolio across multiple asset classes")
    else:
        scores["diversification"] = 0
    
    # 2. Investment Consistency (0-200 points) - SIP analysis
    sip_assets = [asset for asset in assets if asset.is_sip_active]
    sip_score = min(200, len(sip_assets) * 50 + (len(sip_assets) > 0) * 50)
    scores["consistency"] = sip_score
    
    if len(sip_assets) > 0:
        strengths.append(f"Consistent SIP investments in {len(sip_assets)} assets")
    else:
        areas_for_improvement.append("No systematic investment plans (SIPs) active")
        recommendations.append("Consider starting SIPs for regular investing")
    
    # 3. Growth Performance (0-200 points)
    if dashboard.gain_loss_percentage >= 15:
        growth_score = 200
        strengths.append("Excellent portfolio performance")
    elif dashboard.gain_loss_percentage >= 10:
        growth_score = 150
        strengths.append("Good portfolio performance")
    elif dashboard.gain_loss_percentage >= 5:
        growth_score = 100
    elif dashboard.gain_loss_percentage >= 0:
        growth_score = 50
    else:
        growth_score = 0
        areas_for_improvement.append("Portfolio showing negative returns")
        recommendations.append("Review and rebalance portfolio allocation")
    
    scores["performance"] = growth_score
    
    # 4. Net Worth Growth (0-200 points)
    net_worth_tier = dashboard.total_net_worth
    if net_worth_tier >= 10000000:  # 1 crore+
        net_worth_score = 200
        strengths.append("Achieved significant wealth accumulation")
    elif net_worth_tier >= 5000000:  # 50 lakh+
        net_worth_score = 150
        strengths.append("Strong wealth accumulation progress")
    elif net_worth_tier >= 1000000:  # 10 lakh+
        net_worth_score = 100
    elif net_worth_tier >= 500000:  # 5 lakh+
        net_worth_score = 75
    elif net_worth_tier >= 100000:  # 1 lakh+
        net_worth_score = 50
    else:
        net_worth_score = 25
        recommendations.append("Focus on increasing monthly investments")
    
    scores["wealth_accumulation"] = net_worth_score
    
    # 5. Risk Management (0-200 points) - Asset allocation analysis
    risk_score = 100  # Base score
    if dashboard.asset_allocation:
        # Check for high-risk concentration
        risky_assets = ["cryptocurrency", "stocks"]
        risky_allocation = sum(v for k, v in dashboard.asset_allocation.items() if k in risky_assets)
        risky_percentage = risky_allocation / dashboard.total_net_worth * 100
        
        if risky_percentage > 80:
            risk_score = 50
            recommendations.append("Consider reducing high-risk asset concentration")
        elif risky_percentage > 60:
            risk_score = 100
        else:
            risk_score = 150
            strengths.append("Balanced risk allocation")
        
        # Bonus for defensive assets
        safe_assets = ["fixed_deposits", "gold"]
        safe_allocation = sum(v for k, v in dashboard.asset_allocation.items() if k in safe_assets)
        safe_percentage = safe_allocation / dashboard.total_net_worth * 100
        
        if safe_percentage >= 20:
            risk_score += 50
            strengths.append("Good defensive asset allocation")
    
    scores["risk_management"] = min(200, risk_score)
    
    # Calculate overall score
    overall_score = sum(scores.values())
    
    # Add general recommendations
    if overall_score >= 800:
        strengths.append("Excellent overall financial health")
    elif overall_score >= 600:
        recommendations.append("Consider minor optimizations to reach excellent tier")
    elif overall_score >= 400:
        recommendations.append("Focus on diversification and consistent investing")
    else:
        recommendations.append("Significant improvements needed in financial planning")
    
    return FinancialHealthScore(
        overall_score=overall_score,
        category_scores=scores,
        recommendations=recommendations,
        strengths=strengths,
        areas_for_improvement=areas_for_improvement
    )

def calculate_performance_attribution(assets: List[Asset], dashboard: DashboardSummary) -> PerformanceAttribution:
    """Calculate detailed performance attribution analysis"""
    
    asset_contributions = {}
    time_weighted_returns = {}
    best_performers = []
    worst_performers = []
    
    # Calculate contribution by each asset
    for asset in assets:
        gain_loss = asset.current_value - asset.purchase_value
        contribution_to_portfolio = gain_loss / dashboard.total_investment * 100 if dashboard.total_investment > 0 else 0
        asset_contributions[asset.name] = contribution_to_portfolio
        
        # Calculate individual asset return
        asset_return = (asset.current_value - asset.purchase_value) / asset.purchase_value * 100 if asset.purchase_value > 0 else 0
        time_weighted_returns[asset.name] = asset_return
        
        # Track best/worst performers
        asset_data = {
            "name": asset.name,
            "asset_type": asset.asset_type,
            "return_percentage": asset_return,
            "contribution": contribution_to_portfolio,
            "current_value": asset.current_value
        }
        
        if asset_return > 0:
            best_performers.append(asset_data)
        else:
            worst_performers.append(asset_data)
    
    # Sort performers
    best_performers.sort(key=lambda x: x["return_percentage"], reverse=True)
    worst_performers.sort(key=lambda x: x["return_percentage"])
    
    # Sector analysis by asset type
    sector_analysis = {}
    for asset_type, value in dashboard.asset_allocation.items():
        allocation_percentage = value / dashboard.total_net_worth * 100 if dashboard.total_net_worth > 0 else 0
        
        # Calculate sector returns
        sector_assets = [a for a in assets if a.asset_type == asset_type]
        if sector_assets:
            sector_return = sum((a.current_value - a.purchase_value) / a.purchase_value * 100 if a.purchase_value > 0 else 0
                              for a in sector_assets) / len(sector_assets)
        else:
            sector_return = 0
        
        sector_analysis[ASSET_TYPES_DICT.get(asset_type, asset_type)] = {
            "allocation_percentage": allocation_percentage,
            "average_return": sector_return,
            "total_value": value
        }
    
    # Simple correlation matrix (for demonstration)
    correlation_matrix = {}
    asset_types = list(dashboard.asset_allocation.keys())
    for i, type1 in enumerate(asset_types):
        correlation_matrix[ASSET_TYPES_DICT.get(type1, type1)] = {}
        for j, type2 in enumerate(asset_types):
            # Simplified correlation (in real world, you'd use price history)
            if i == j:
                correlation = 1.0
            else:
                correlation = np.random.uniform(0.1, 0.8)  # Mock correlation
            correlation_matrix[ASSET_TYPES_DICT.get(type1, type1)][ASSET_TYPES_DICT.get(type2, type2)] = round(correlation, 2)
    
    return PerformanceAttribution(
        asset_contributions=asset_contributions,
        sector_analysis=sector_analysis,
        time_weighted_returns=time_weighted_returns,
        best_performers=best_performers[:5],  # Top 5
        worst_performers=worst_performers[:5],  # Bottom 5
        correlation_matrix=correlation_matrix
    )

def calculate_tax_optimization(assets: List[Asset]) -> TaxOptimization:
    """Calculate comprehensive tax optimization analysis"""
    
    current_date = datetime.now()
    ltcg_liability = 0
    stcg_liability = 0
    tax_saving_opportunities = []
    harvesting_suggestions = []
    
    # Indian tax rates (as of 2024)
    LTCG_RATE = 0.125  # 12.5% on gains above 1.25 lakh
    STCG_RATE = 0.20   # 20% on short term gains
    LTCG_EXEMPTION = 125000  # 1.25 lakh exemption for LTCG
    
    total_ltcg = 0
    total_stcg = 0
    
    for asset in assets:
        purchase_date = asset.purchase_date
        gain_loss = asset.current_value - asset.purchase_value
        
        if gain_loss > 0:  # Only tax on gains
            # Determine if LTCG or STCG based on holding period
            holding_days = (current_date - purchase_date).days
            
            # For equity/equity MF: >365 days = LTCG, else STCG
            # For other assets: >36 months = LTCG, else STCG
            is_equity = asset.asset_type in ["stocks", "mutual_funds", "cryptocurrency"]
            ltcg_threshold_days = 365 if is_equity else 1095  # 36 months
            
            if holding_days > ltcg_threshold_days:
                total_ltcg += gain_loss
            else:
                total_stcg += gain_loss
                
                # Suggest holding for LTCG if close to threshold
                days_to_ltcg = ltcg_threshold_days - holding_days
                if days_to_ltcg <= 90 and days_to_ltcg > 0:
                    tax_saving_opportunities.append({
                        "type": "hold_for_ltcg",
                        "asset_name": asset.name,
                        "days_remaining": days_to_ltcg,
                        "potential_tax_saving": gain_loss * (STCG_RATE - LTCG_RATE),
                        "description": f"Hold {asset.name} for {days_to_ltcg} more days to qualify for LTCG"
                    })
        else:
            # Loss harvesting opportunity
            harvesting_suggestions.append({
                "type": "loss_harvesting",
                "asset_name": asset.name,
                "loss_amount": abs(gain_loss),
                "tax_benefit": abs(gain_loss) * 0.30,  # Assuming 30% tax bracket
                "description": f"Realize loss of ₹{abs(gain_loss):,.0f} to offset gains"
            })
    
    # Calculate actual tax liability
    ltcg_taxable = max(0, total_ltcg - LTCG_EXEMPTION)
    ltcg_liability = ltcg_taxable * LTCG_RATE
    stcg_liability = total_stcg * STCG_RATE
    
    total_tax_liability = ltcg_liability + stcg_liability
    total_gains = total_ltcg + total_stcg
    effective_tax_rate = (total_tax_liability / total_gains * 100) if total_gains > 0 else 0
    
    # Add general tax saving opportunities
    if total_ltcg > LTCG_EXEMPTION * 2:
        tax_saving_opportunities.append({
            "type": "ltcg_planning",
            "description": "Consider staggered profit booking across financial years",
            "potential_saving": (total_ltcg - LTCG_EXEMPTION) * LTCG_RATE * 0.3
        })
    
    current_year_tax = {
        "ltcg_gains": total_ltcg,
        "stcg_gains": total_stcg,
        "ltcg_exemption_used": min(total_ltcg, LTCG_EXEMPTION),
        "ltcg_exemption_remaining": max(0, LTCG_EXEMPTION - total_ltcg)
    }
    
    return TaxOptimization(
        current_year_tax=current_year_tax,
        ltcg_liability=ltcg_liability,
        stcg_liability=stcg_liability,
        tax_saving_opportunities=tax_saving_opportunities,
        harvesting_suggestions=harvesting_suggestions,
        total_tax_liability=total_tax_liability,
        effective_tax_rate=effective_tax_rate
    )

def calculate_compound_growth(principal: float, annual_rate: float, annual_investment: float, years: int, 
                            monthly_sip: float = 0, step_up_percentage: float = 0) -> List[ProjectionResult]:
    """Calculate compound growth with annual investments and SIPs with step-ups"""
    results = []
    current_value = principal
    current_monthly_sip = monthly_sip
    
    for year in range(1, years + 1):
        # SIP contributions for the year (monthly compounding)
        year_sip_contribution = 0
        year_start_value = current_value
        
        # Monthly SIP processing
        for month in range(1, 13):
            # Add monthly SIP at the beginning of each month
            if current_monthly_sip > 0:
                current_value += current_monthly_sip
                year_sip_contribution += current_monthly_sip
            
            # Apply monthly growth rate
            monthly_rate = annual_rate / 100 / 12
            current_value *= (1 + monthly_rate)
        
        # Add annual lump sum investment at year end
        current_value += annual_investment
        
        # Calculate total growth for the year
        year_end_value_without_investments = year_start_value * ((1 + annual_rate / 100) ** 1)
        growth = current_value - year_start_value - year_sip_contribution - annual_investment
        
        results.append(ProjectionResult(
            year=year,
            total_value=current_value,
            investment_added=annual_investment,
            growth=growth,
            sip_contribution=year_sip_contribution,
            lumpsum_contribution=annual_investment
        ))
        
        # Apply step-up to SIP for next year
        if step_up_percentage > 0:
            current_monthly_sip *= (1 + step_up_percentage / 100)
    
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
    """Calculate net worth projections based on current assets and growth rates with SIP support"""
    
    total_projections = []
    years = max(p.years for p in projections) if projections else 10
    
    # Initialize yearly totals
    yearly_totals = {year: {
        "total_value": 0, 
        "total_investment": 0, 
        "total_growth": 0,
        "total_sip_contribution": 0,
        "total_lumpsum_contribution": 0
    } for year in range(1, years + 1)}
    
    # Calculate each asset class projection
    for projection in projections:
        asset_projections = calculate_compound_growth(
            projection.current_value,
            projection.annual_growth_rate,
            projection.annual_investment,
            projection.years,
            projection.monthly_sip_amount,
            projection.step_up_percentage
        )
        
        # Add to yearly totals
        for result in asset_projections:
            if result.year <= years:
                yearly_totals[result.year]["total_value"] += result.total_value
                yearly_totals[result.year]["total_investment"] += result.investment_added
                yearly_totals[result.year]["total_growth"] += result.growth
                yearly_totals[result.year]["total_sip_contribution"] += result.sip_contribution
                yearly_totals[result.year]["total_lumpsum_contribution"] += result.lumpsum_contribution
    
    # Convert to list format
    for year in range(1, years + 1):
        total_projections.append({
            "year": year,
            "total_value": yearly_totals[year]["total_value"],
            "investment_added": yearly_totals[year]["total_investment"],
            "growth": yearly_totals[year]["total_growth"],
            "sip_contribution": yearly_totals[year]["total_sip_contribution"],
            "lumpsum_contribution": yearly_totals[year]["total_lumpsum_contribution"]
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
