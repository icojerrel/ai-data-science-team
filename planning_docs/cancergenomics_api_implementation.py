"""
CancerGenomics.AI - FastAPI Backend Implementation
MVP version using ai-data-science-team library + OpenRouter

This is the core API that powers the CancerGenomics.AI platform.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
import pandas as pd
import uuid
from datetime import datetime, timedelta
import os
from pathlib import Path
import jwt

# Import our AI Data Science Team library (already built!)
from ai_data_science_team.ml_agents import GenomicsAnalysisAgent
from ai_data_science_team.utils.openrouter import get_openrouter_llm, get_cost_estimate

# Database (use SQLAlchemy + PostgreSQL in production)
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Redis for caching and task queue
from redis import Redis
from rq import Queue

# Payment processing
import stripe

# PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

# ============================================================================
# Configuration
# ============================================================================

app = FastAPI(
    title="CancerGenomics.AI API",
    description="AI-powered cancer genomics analysis at 1/100th the cost",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://cancergenomics.ai"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/cancergenomics")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")

# Stripe setup
stripe.api_key = STRIPE_SECRET_KEY

# Redis setup for background tasks
redis_conn = Redis.from_url(REDIS_URL)
task_queue = Queue(connection=redis_conn)

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ============================================================================
# Database Models
# ============================================================================

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    organization = Column(String)
    plan = Column(String, default="free")  # free, starter, pro, enterprise
    credits_remaining = Column(Integer, default=10)  # Free tier: 10 samples
    stripe_customer_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    progress = Column(Integer, default=0)

    # Analysis options
    driver_genes = Column(Boolean, default=True)
    pathway_enrichment = Column(Boolean, default=True)
    tmb_calculation = Column(Boolean, default=True)
    actionable_mutations = Column(Boolean, default=True)

    # Results (stored as JSON)
    results = Column(JSON)

    # Metadata
    sample_count = Column(Integer)
    cost_credits = Column(Integer, default=1)
    model_used = Column(String, default="deepseek/deepseek-chat")
    api_cost = Column(Float)  # Actual OpenRouter cost

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    # File paths
    upload_path = Column(String)
    report_path = Column(String)


Base.metadata.create_all(engine)

# ============================================================================
# Pydantic Models (API Request/Response)
# ============================================================================

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    organization: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    organization: Optional[str]
    plan: str
    credits_remaining: int


class AnalysisRequest(BaseModel):
    driver_genes: bool = True
    pathway_enrichment: bool = True
    tmb_calculation: bool = True
    actionable_mutations: bool = True


class AnalysisResponse(BaseModel):
    analysis_id: str
    status: str
    estimated_time: int  # seconds
    cost_credits: int


class AnalysisStatus(BaseModel):
    analysis_id: str
    status: str
    progress: int
    results_url: Optional[str]
    report_url: Optional[str]


# ============================================================================
# Authentication
# ============================================================================

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_jwt_token(user_id: str) -> str:
    """Create JWT token for user authentication"""
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_jwt_token(token: str) -> str:
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    token: str = Depends(lambda: None),  # Get from Authorization header
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = verify_jwt_token(token)
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/api/v1/auth/register", response_model=UserResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register new user"""

    # Check if user already exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password (use bcrypt in production)
    password_hash = user_data.password  # TODO: Replace with bcrypt

    # Create user
    user = User(
        email=user_data.email,
        password_hash=password_hash,
        organization=user_data.organization,
        plan="free",
        credits_remaining=10  # Free tier
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        organization=user.organization,
        plan=user.plan,
        credits_remaining=user.credits_remaining
    )


@app.post("/api/v1/auth/login")
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login user and return JWT token"""

    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or user.password_hash != credentials.password:  # TODO: Use bcrypt
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create JWT token
    token = create_jwt_token(user.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse(
            id=user.id,
            email=user.email,
            organization=user.organization,
            plan=user.plan,
            credits_remaining=user.credits_remaining
        )
    }


# ============================================================================
# Analysis Endpoints
# ============================================================================

@app.post("/api/v1/analyze", response_model=AnalysisResponse)
async def create_analysis(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload mutation data and create analysis job.

    Accepts CSV or VCF files with mutation data.
    Returns analysis_id for tracking progress.
    """

    # Check credits
    if user.credits_remaining < 1:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. You have {user.credits_remaining} credits remaining."
        )

    # Validate file type
    if not file.filename.endswith(('.csv', '.vcf', '.tsv')):
        raise HTTPException(
            status_code=400,
            detail="Only CSV and VCF files are supported"
        )

    # Create analysis record
    analysis = Analysis(
        user_id=user.id,
        filename=file.filename,
        status="pending",
        cost_credits=1
    )

    # Save uploaded file
    upload_dir = Path("uploads") / user.id
    upload_dir.mkdir(parents=True, exist_ok=True)
    upload_path = upload_dir / f"{analysis.id}_{file.filename}"

    with open(upload_path, "wb") as f:
        content = await file.read()
        f.write(content)

    analysis.upload_path = str(upload_path)

    # Add to database
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Queue background job for processing
    task_queue.enqueue(
        process_analysis,
        analysis_id=analysis.id,
        user_id=user.id
    )

    return AnalysisResponse(
        analysis_id=analysis.id,
        status="pending",
        estimated_time=120,  # 2 minutes
        cost_credits=1
    )


async def process_analysis(analysis_id: str, user_id: str):
    """
    Background task to process genomics analysis.

    This runs the GenomicsAnalysisAgent on uploaded mutation data.
    """

    db = SessionLocal()

    try:
        # Get analysis record
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            return

        # Update status
        analysis.status = "processing"
        analysis.progress = 10
        db.commit()

        # Load mutation data
        mutations = pd.read_csv(analysis.upload_path)
        analysis.sample_count = len(mutations)
        analysis.progress = 20
        db.commit()

        # Determine which model to use based on user plan
        user = db.query(User).filter(User.id == user_id).first()

        if user.plan == "enterprise":
            model = "anthropic/claude-3.5-sonnet"  # Premium quality
        elif user.plan == "pro":
            model = "anthropic/claude-3-haiku"  # Good quality, cheap
        else:
            model = "deepseek/deepseek-chat"  # Ultra-budget

        # Initialize LLM with OpenRouter
        llm = get_openrouter_llm(model, temperature=0)

        analysis.model_used = model
        analysis.progress = 30
        db.commit()

        # Initialize GenomicsAnalysisAgent (our existing agent!)
        genomics_agent = GenomicsAnalysisAgent(
            model=llm,
            gene_column="gene",  # Adjust based on file format
            mutation_column="mutation_type",
            log=True,
            log_path=f"logs/{analysis_id}"
        )

        analysis.progress = 40
        db.commit()

        # Build analysis instructions
        instructions = []
        if analysis.driver_genes:
            instructions.append("Identify top 20 cancer driver genes")
        if analysis.pathway_enrichment:
            instructions.append("Perform pathway enrichment for major cancer pathways")
        if analysis.tmb_calculation:
            instructions.append("Calculate tumor mutational burden (TMB) per sample")
        if analysis.actionable_mutations:
            instructions.append("Identify actionable mutations (BRAF V600E, EGFR, KRAS, etc.)")

        instruction_text = ". ".join(instructions) + "."

        analysis.progress = 50
        db.commit()

        # Run the analysis! (This is where the magic happens)
        genomics_agent.invoke_agent(
            data_raw=mutations,
            user_instructions=instruction_text
        )

        analysis.progress = 80
        db.commit()

        # Get results
        results = genomics_agent.get_genomics_results()

        # Store results as JSON
        analysis.results = results
        analysis.progress = 90
        db.commit()

        # Generate PDF report
        report_path = generate_pdf_report(analysis, results)
        analysis.report_path = report_path

        # Estimate API cost (for analytics)
        # Approximate: 50K input tokens, 10K output tokens
        cost_estimate = get_cost_estimate(
            model=model,
            input_tokens=50000,
            output_tokens=10000
        )
        analysis.api_cost = cost_estimate["total"]

        # Deduct credits from user
        user.credits_remaining -= 1

        # Mark as completed
        analysis.status = "completed"
        analysis.progress = 100
        analysis.completed_at = datetime.utcnow()

        db.commit()

    except Exception as e:
        # Mark as failed
        analysis.status = "failed"
        analysis.results = {"error": str(e)}
        db.commit()

    finally:
        db.close()


@app.get("/api/v1/analysis/{analysis_id}", response_model=AnalysisStatus)
async def get_analysis_status(
    analysis_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get status of analysis job"""

    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user.id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return AnalysisStatus(
        analysis_id=analysis.id,
        status=analysis.status,
        progress=analysis.progress,
        results_url=f"/api/v1/analysis/{analysis_id}/results" if analysis.status == "completed" else None,
        report_url=f"/api/v1/analysis/{analysis_id}/report.pdf" if analysis.status == "completed" else None
    )


@app.get("/api/v1/analysis/{analysis_id}/results")
async def get_analysis_results(
    analysis_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analysis results (JSON)"""

    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user.id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if analysis.status != "completed":
        raise HTTPException(status_code=400, detail="Analysis not completed yet")

    return analysis.results


@app.get("/api/v1/analysis/{analysis_id}/report.pdf")
async def download_report(
    analysis_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download PDF report"""

    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user.id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if not analysis.report_path or not Path(analysis.report_path).exists():
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(
        analysis.report_path,
        filename=f"cancergenomics_report_{analysis_id}.pdf",
        media_type="application/pdf"
    )


# ============================================================================
# Payment Endpoints (Stripe)
# ============================================================================

@app.post("/api/v1/subscribe")
async def create_subscription(
    plan: str,  # starter, pro, enterprise
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create Stripe subscription for user"""

    # Pricing (match business plan)
    price_ids = {
        "starter": "price_starter_99",  # $99/month
        "pro": "price_pro_299",  # $299/month
        "enterprise": "price_enterprise_999"  # $999/month
    }

    if plan not in price_ids:
        raise HTTPException(status_code=400, detail="Invalid plan")

    # Create Stripe customer if not exists
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": user.id}
        )
        user.stripe_customer_id = customer.id
        db.commit()

    # Create subscription
    subscription = stripe.Subscription.create(
        customer=user.stripe_customer_id,
        items=[{"price": price_ids[plan]}],
        payment_behavior="default_incomplete",
        expand=["latest_invoice.payment_intent"]
    )

    # Update user plan
    user.plan = plan

    # Grant credits based on plan
    credits = {
        "starter": 50,
        "pro": 200,
        "enterprise": 1000
    }
    user.credits_remaining = credits[plan]

    db.commit()

    return {
        "subscription_id": subscription.id,
        "client_secret": subscription.latest_invoice.payment_intent.client_secret
    }


# ============================================================================
# Helper Functions
# ============================================================================

def generate_pdf_report(analysis: Analysis, results: dict) -> str:
    """Generate PDF report from analysis results"""

    report_dir = Path("reports") / analysis.user_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{analysis.id}_report.pdf"

    # Create PDF
    c = canvas.Canvas(str(report_path), pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawString(1*inch, height - 1*inch, "CancerGenomics.AI Report")

    # Metadata
    c.setFont("Helvetica", 12)
    c.drawString(1*inch, height - 1.5*inch, f"Analysis ID: {analysis.id}")
    c.drawString(1*inch, height - 1.7*inch, f"Date: {analysis.completed_at.strftime('%Y-%m-%d')}")
    c.drawString(1*inch, height - 1.9*inch, f"Samples: {analysis.sample_count}")

    # Driver Genes
    y = height - 2.5*inch
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, y, "Top Driver Genes")

    y -= 0.3*inch
    c.setFont("Helvetica", 10)

    if "driver_genes" in results:
        for gene in results["driver_genes"][:10]:
            c.drawString(1*inch, y, f"• {gene['gene']}: {gene['mutations']} mutations ({gene['frequency']*100:.1f}%)")
            y -= 0.2*inch

    # Pathway Enrichment
    y -= 0.3*inch
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, y, "Pathway Enrichment")

    y -= 0.3*inch
    c.setFont("Helvetica", 10)

    if "pathways" in results:
        for pathway, data in list(results["pathways"].items())[:5]:
            c.drawString(1*inch, y, f"• {pathway}: p-value = {data['p_value']}")
            y -= 0.2*inch

    # TMB
    y -= 0.3*inch
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, y, "Tumor Mutational Burden")

    y -= 0.3*inch
    c.setFont("Helvetica", 10)

    if "tmb" in results:
        tmb = results["tmb"]
        c.drawString(1*inch, y, f"TMB: {tmb['mutations_per_mb']} mutations/Mb")
        y -= 0.2*inch
        c.drawString(1*inch, y, f"Immunotherapy Eligible: {'Yes' if tmb['immunotherapy_eligible'] else 'No'}")

    # Footer
    c.setFont("Helvetica", 8)
    c.drawString(1*inch, 0.5*inch, "Generated by CancerGenomics.AI - For Research Use Only")
    c.drawString(1*inch, 0.3*inch, "https://cancergenomics.ai")

    c.save()

    return str(report_path)


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
