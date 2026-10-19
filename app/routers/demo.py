from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.activity import Activity, ActivityType
from app.models.audit_log import AuditLog
from app.models.lead import Lead, LeadSource, LeadStatus
from app.models.task import FollowUpTask, TaskStatus
from app.models.user import RoleEnum, User
from app.services.auth_service import create_access_token, get_password_hash
from app.services.scoring_service import recalculate_and_save_lead_score

router = APIRouter(prefix="/api/v1/demo", tags=["Demo & Seeding"])


@router.post("/seed", status_code=status.HTTP_201_CREATED)
async def seed_demo_data(db: AsyncSession = Depends(get_db)):
    """
    Populate database with rich, realistic demonstration data for college presentations.
    Creates default admin & member accounts, 7 enterprise leads, activities, and tasks.
    """
    # 1. Ensure or create Demo Admin
    admin_stmt = select(User).where(User.email == "admin@leadforge.dev")
    admin_user = (await db.execute(admin_stmt)).scalar_one_or_none()
    if not admin_user:
        admin_user = User(
            name="Alex Morgan (Admin)",
            email="admin@leadforge.dev",
            password_hash=get_password_hash("admin123"),
            role=RoleEnum.admin,
        )
        db.add(admin_user)
        await db.flush()

    # 2. Ensure or create Demo Sales Rep
    sales_stmt = select(User).where(User.email == "sales@leadforge.dev")
    sales_user = (await db.execute(sales_stmt)).scalar_one_or_none()
    if not sales_user:
        sales_user = User(
            name="Sarah Jenkins (Sales Rep)",
            email="sales@leadforge.dev",
            password_hash=get_password_hash("sales123"),
            role=RoleEnum.member,
        )
        db.add(sales_user)
        await db.flush()

    now = datetime.now(timezone.utc)

    # 3. Sample Leads Data
    demo_leads_specs = [
        {
            "name": "David Sterling",
            "company": "Apex Financial Technologies",
            "email": "david.sterling@apexfin.io",
            "phone": "+1 (555) 234-8901",
            "source": LeadSource.linkedin,
            "status": LeadStatus.proposal,
            "notes": "Enterprise FinTech seeking automated lead scoring and CRM integration. Budget $45k/year approved.",
            "owner_id": admin_user.id,
            "activities": [
                (ActivityType.call, "Initial discovery call with Head of Sales. Highly engaged with security features."),
                (ActivityType.meeting, "Product demo with 5 team leads. Presented custom scoring models and SLA guarantees."),
                (ActivityType.email, "Sent proposal document and SOC2 compliance package.")
            ],
            "tasks": [
                ("Follow-up on proposal review", "Check in with David regarding board approval timeline.", now + timedelta(days=2)),
            ]
        },
        {
            "name": "Dr. Elena Rostova",
            "company": "Nexus Health Analytics",
            "email": "elena.rostova@nexushealth.org",
            "phone": "+1 (555) 987-6543",
            "source": LeadSource.web_form,
            "status": LeadStatus.won,
            "notes": "Healthcare data provider. Contract signed for 24-month multi-seat license.",
            "owner_id": sales_user.id,
            "activities": [
                (ActivityType.email, "Inbound enquiry from website demo request form."),
                (ActivityType.meeting, "Technical architecture review with Lead Engineer."),
                (ActivityType.call, "Commercial negotiation call - contract terms agreed."),
                (ActivityType.note, "Contract executed by Legal. Onboarding scheduled for next Monday.")
            ],
            "tasks": [
                ("Conduct onboarding kick-off", "Schedule 60-min session with clinical analytics team.", now + timedelta(days=5)),
            ]
        },
        {
            "name": "Marcus Vance",
            "company": "CloudScale DevOps Inc",
            "email": "m.vance@cloudscale.net",
            "phone": "+1 (555) 345-6789",
            "source": LeadSource.referral,
            "status": LeadStatus.qualified,
            "notes": "Referred by Nexus Health. Needs high-throughput REST API access and webhook webhooks.",
            "owner_id": sales_user.id,
            "activities": [
                (ActivityType.call, "Warm intro call. Discussed migration from legacy Salesforce pipeline."),
                (ActivityType.meeting, "Completed API endpoints deep-dive with engineering director.")
            ],
            "tasks": [
                ("Send benchmark performance reports", "Share stress test results and API response time metrics.", now + timedelta(days=1)),
            ]
        },
        {
            "name": "Sophia Chen",
            "company": "Starlight Robotics AI",
            "email": "sophia.chen@starlight-ai.com",
            "phone": "+1 (555) 456-7890",
            "source": LeadSource.web_form,
            "status": LeadStatus.contacted,
            "notes": "Autonomous robotics startup. Exploring automated customer query routing.",
            "owner_id": admin_user.id,
            "activities": [
                (ActivityType.email, "Sent introductory platform overview and video walkthrough.")
            ],
            "tasks": [
                ("Schedule 15-min discovery call", "Confirm availability for Tuesday afternoon demo.", now + timedelta(days=3)),
            ]
        },
        {
            "name": "Liam O'Connor",
            "company": "GreenGrid Energy Systems",
            "email": "liam@greengrid.eu",
            "phone": "+44 20 7946 0912",
            "source": LeadSource.cold_call,
            "status": LeadStatus.new,
            "notes": "Renewable energy equipment distributor looking to modernize their lead intake funnel.",
            "owner_id": sales_user.id,
            "activities": [],
            "tasks": [
                ("Send cold outreach sequence #1", "Personalized email highlighting ROI in clean tech sector.", now + timedelta(hours=6)),
            ]
        },
        {
            "name": "Amina Al-Mansoor",
            "company": "Falcon Logistics Global",
            "email": "amina@falconlogistics.ae",
            "phone": "+971 4 321 0987",
            "source": LeadSource.linkedin,
            "status": LeadStatus.proposal,
            "notes": "Freight forwarding company with 80+ agents. Demanded multi-user role permissions.",
            "owner_id": admin_user.id,
            "activities": [
                (ActivityType.call, "Introductory discussion with Regional Director."),
                (ActivityType.meeting, "Custom workflow workshop with operations managers."),
                (ActivityType.email, "Shared custom enterprise SLA proposal.")
            ],
            "tasks": [
                ("Follow up on procurement approval", "Legal team currently reviewing data sovereignty terms.", now + timedelta(days=4)),
            ]
        },
        {
            "name": "Kavita Sharma",
            "company": "Zenith Retail Solutions",
            "email": "kavita.s@zenithretail.in",
            "phone": "+91 98200 12345",
            "source": LeadSource.referral,
            "status": LeadStatus.new,
            "notes": "Omnichannel retail platform. Evaluating alternatives to costly enterprise CRMs.",
            "owner_id": sales_user.id,
            "activities": [],
            "tasks": [
                ("Initial phone introduction", "Introduce LeadForge scoring capabilities.", now + timedelta(days=1)),
            ]
        }
    ]

    created_leads_count = 0

    for spec in demo_leads_specs:
        # Check if lead with this email already exists
        lead_stmt = select(Lead).where(Lead.email == spec["email"])
        existing_lead = (await db.execute(lead_stmt)).scalar_one_or_none()

        if not existing_lead:
            lead = Lead(
                name=spec["name"],
                email=spec["email"],
                company=spec["company"],
                phone=spec["phone"],
                source=spec["source"],
                status=spec["status"],
                notes=spec["notes"],
                owner_id=spec["owner_id"],
                score=0,
            )
            db.add(lead)
            await db.flush()

            # Add activities
            for act_type, act_notes in spec["activities"]:
                act = Activity(
                    lead_id=lead.id,
                    actor_id=spec["owner_id"],
                    type=act_type,
                    notes=act_notes,
                )
                db.add(act)

            # Add tasks
            for task_title, task_desc, due in spec["tasks"]:
                task = FollowUpTask(
                    lead_id=lead.id,
                    assignee_id=spec["owner_id"],
                    title=task_title,
                    description=task_desc,
                    due_at=due,
                    status=TaskStatus.pending,
                )
                db.add(task)

            await db.flush()

            # Automatically compute and store the explainable AI score
            await recalculate_and_save_lead_score(db=db, lead=lead, actor_id=spec["owner_id"])
            created_leads_count += 1

    await db.commit()

    # Generate ready-to-use tokens for fast 1-click login
    admin_token = create_access_token(data={"sub": admin_user.id, "email": admin_user.email, "role": admin_user.role.value})
    sales_token = create_access_token(data={"sub": sales_user.id, "email": sales_user.email, "role": sales_user.role.value})

    return {
        "status": "success",
        "message": f"Demo environment seeded successfully. {created_leads_count} new leads added.",
        "demo_accounts": {
            "admin": {
                "name": admin_user.name,
                "email": admin_user.email,
                "password": "admin123",
                "token": admin_token,
            },
            "sales_rep": {
                "name": sales_user.name,
                "email": sales_user.email,
                "password": "sales123",
                "token": sales_token,
            }
        }
    }


@router.get("/quick-auth", status_code=status.HTTP_200_OK)
async def quick_demo_auth(account: str = "admin", db: AsyncSession = Depends(get_db)):
    """
    Get immediate authentication token for instant demo login without typing credentials.
    Account can be 'admin' or 'sales'.
    """
    email = "admin@leadforge.dev" if account == "admin" else "sales@leadforge.dev"
    stmt = select(User).where(User.email == email)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        # Seed if users don't exist yet
        await seed_demo_data(db)
        user = (await db.execute(stmt)).scalar_one_or_none()

    token = create_access_token(data={"sub": user.id, "email": user.email, "role": user.role.value})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
    }
