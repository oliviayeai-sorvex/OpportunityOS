import os
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.router import ControlPlaneAPI
from services.auth_service import AuthContext, AuthService

app = FastAPI(title="OpportunityOS", version="0.3")
api = ControlPlaneAPI()
auth = AuthService()

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:4173,http://127.0.0.1:4173,http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

def get_ctx(request: Request) -> AuthContext:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    token = auth_header[7:]
    try:
        return auth.verify_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=str(exc))

@app.exception_handler(PermissionError)
async def permission_exception_handler(request: Request, exc: PermissionError):
    return JSONResponse(status_code=401, content={"error": str(exc)})

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=400, content={"error": str(exc)})


@app.get("/health")
def health():
    return {"status": "ok", "supabase_enabled": auth.is_supabase_enabled()}

@app.get("/api/v1/dashboard/summary")
def dashboard_summary(ctx: AuthContext = Depends(get_ctx)):
    return api.dashboard_summary(role=ctx.role)

@app.get("/api/v1/watchlists")
def list_watchlists(ctx: AuthContext = Depends(get_ctx)):
    return api.list_watchlist(role=ctx.role, user_id=ctx.user_id)

@app.get("/api/v1/grant-writer/dashboard")
def grant_writer_dashboard(ctx: AuthContext = Depends(get_ctx)):
    return api.grant_writer_dashboard(role=ctx.role, user_id=ctx.user_id)

@app.get("/api/v1/grant-writer/board")
def grant_writer_board(
    request: Request,
    ctx: AuthContext = Depends(get_ctx)
):
    filters = {}
    for key in ["state", "sector", "min_score", "max_score"]:
        if key in request.query_params:
            filters[key] = request.query_params[key]
    sort_by = request.query_params.get("sort_by", "deadline")
    return api.grant_writer_board(role=ctx.role, user_id=ctx.user_id, filters=filters, sort_by=sort_by)

@app.get("/api/v1/grant-writer/drafts")
def grant_writer_drafts(grant_result_id: str = "", ctx: AuthContext = Depends(get_ctx)):
    return api.grant_writer_drafts(role=ctx.role, user_id=ctx.user_id, grant_result_id=grant_result_id)

@app.get("/api/v1/grant-writer/pipeline")
def grant_writer_pipeline(run_id: str = "", ctx: AuthContext = Depends(get_ctx)):
    return api.grant_writer_pipeline_details(role=ctx.role, user_id=ctx.user_id, run_id=run_id)

@app.get("/api/v1/grant-writer/discovery/debug")
def discovery_debug(source_id: str = "", ctx: AuthContext = Depends(get_ctx)):
    return api.grant_writer_discovery_debug(role=ctx.role, user_id=ctx.user_id, source_id=source_id)

@app.get("/api/v1/settings")
def get_settings(ctx: AuthContext = Depends(get_ctx)):
    return api.get_settings(role=ctx.role, user_id=ctx.user_id, email=ctx.email)

@app.get("/api/v1/home")
def home(ctx: AuthContext = Depends(get_ctx)):
    return api.home_shell(role=ctx.role, user_id=ctx.user_id)

@app.get("/api/v1/jobs")
def jobs(vertical: str = "", ctx: AuthContext = Depends(get_ctx)):
    return api.scheduler_jobs(role=ctx.role, user_id=ctx.user_id, vertical=vertical)

@app.get("/api/v1/notifications")
def notifications(unread_only: bool = False, ctx: AuthContext = Depends(get_ctx)):
    return api.notifications(role=ctx.role, user_id=ctx.user_id, unread_only=unread_only)

@app.post("/api/v1/auth/signup")
def signup(payload: dict):
    return auth.sign_up(email=payload.get("email"), password=payload.get("password"))

@app.post("/api/v1/auth/login")
def login(payload: dict):
    return auth.login(email=payload.get("email"), password=payload.get("password"))

@app.post("/api/v1/auth/password-reset")
def password_reset(payload: dict):
    return auth.reset_password(email=payload.get("email"))

@app.post("/api/v1/ingestion/run")
def ingestion_run(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.run_ingestion(
        role=ctx.role, 
        sources=payload.get("sources", ["stocks", "real_estate", "grants"]), 
        trace_id=payload.get("trace_id")
    )

@app.post("/api/v1/opportunities/list")
def opportunities_list(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.list_opportunities(role=ctx.role, filters=payload.get("filters", {}))

@app.post("/api/v1/verification")
def verification(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.verify_opportunity(
        role=ctx.role,
        opportunity_id=payload["opportunity_id"],
        actor_id=ctx.user_id,
        status=payload["status"],
        reason=payload["reason"]
    )

@app.post("/api/v1/watchlists/add")
def watchlists_add(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.add_watchlist(role=ctx.role, user_id=ctx.user_id, opportunity_id=payload["opportunity_id"])

@app.post("/api/v1/actions")
def actions(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.create_action(
        role=ctx.role,
        opportunity_id=payload["opportunity_id"],
        owner_id=ctx.user_id,
        summary=payload["summary"],
        due_date=payload["due_date"]
    )

@app.post("/api/v1/actions/list")
def actions_list(ctx: AuthContext = Depends(get_ctx)):
    return api.list_actions(role=ctx.role, owner_id=ctx.user_id)

@app.post("/api/v1/grant-writer/sources/upsert")
def sources_upsert(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.grant_writer_upsert_source(
        role=ctx.role,
        user_id=ctx.user_id,
        source_id=payload["source_id"],
        name=payload["name"],
        url=payload["url"],
        access=payload.get("access", "Public"),
        active=payload.get("active", True)
    )

@app.post("/api/v1/grant-writer/sources/delete")
def sources_delete(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.grant_writer_delete_source(role=ctx.role, user_id=ctx.user_id, source_id=payload["source_id"])

@app.post("/api/v1/grant-writer/sources/reset-defaults")
def sources_reset(ctx: AuthContext = Depends(get_ctx)):
    return api.grant_writer_reset_sources_to_defaults(role=ctx.role, user_id=ctx.user_id)

@app.post("/api/v1/grant-writer/schedule")
def writer_schedule(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.grant_writer_set_schedule(role=ctx.role, user_id=ctx.user_id, frequency=payload["frequency"])

@app.post("/api/v1/grant-writer/scan")
def writer_scan(ctx: AuthContext = Depends(get_ctx)):
    return api.grant_writer_run_scan(role=ctx.role, user_id=ctx.user_id)

@app.post("/api/v1/grant-writer/pipeline/run")
def pipeline_run(ctx: AuthContext = Depends(get_ctx)):
    return api.grant_writer_pipeline_run(role=ctx.role, user_id=ctx.user_id)

@app.post("/api/v1/grant-writer/board/move")
def board_move(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.grant_writer_move_status(
        role=ctx.role,
        user_id=ctx.user_id,
        grant_result_id=payload["grant_result_id"],
        workflow_status=payload["workflow_status"]
    )

@app.post("/api/v1/grant-writer/mark-reviewed")
def mark_reviewed(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.grant_writer_mark_reviewed(
        role=ctx.role,
        user_id=ctx.user_id,
        grant_result_id=payload["grant_result_id"]
    )

@app.post("/api/v1/grant-writer/mark-submitted")
def mark_submitted(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.grant_writer_mark_submitted(
        role=ctx.role,
        user_id=ctx.user_id,
        grant_result_id=payload["grant_result_id"]
    )

@app.post("/api/v1/grant-writer/tracking")
def tracking(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.grant_writer_update_tracking(
        role=ctx.role,
        user_id=ctx.user_id,
        grant_result_id=payload["grant_result_id"],
        notes=payload.get("notes", ""),
        outcome=payload.get("outcome", "Pending"),
        contact_names=payload.get("contact_names", ""),
        reference_numbers=payload.get("reference_numbers", "")
    )

@app.post("/api/v1/grant-writer/draft")
def writer_draft(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.grant_writer_draft(
        role=ctx.role,
        user_id=ctx.user_id,
        grant_result_id=payload["grant_result_id"],
        prompt=payload.get("prompt", "")
    )

@app.post("/api/v1/settings")
def post_settings(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.update_settings(role=ctx.role, user_id=ctx.user_id, email=ctx.email, updates=payload)

@app.post("/api/v1/jobs/run-now")
def jobs_run_now(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.scheduler_run_now(
        role=ctx.role,
        user_id=ctx.user_id,
        vertical=payload.get("vertical", "grants"),
        job_type=payload.get("job_type", "scan")
    )

@app.post("/api/v1/jobs/process")
def jobs_process(ctx: AuthContext = Depends(get_ctx)):
    return api.scheduler_process(role=ctx.role)

@app.post("/api/v1/jobs/digest/run")
def digest_run(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.scheduler_run_now(
        role=ctx.role,
        user_id=ctx.user_id,
        vertical=payload.get("vertical", "grants"),
        job_type="digest"
    )

@app.post("/api/v1/notifications/read")
def notifications_read(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.notification_mark_read(role=ctx.role, user_id=ctx.user_id, notification_id=payload["notification_id"])

@app.post("/api/v1/search")
def search(payload: dict, ctx: AuthContext = Depends(get_ctx)):
    return api.global_search(role=ctx.role, user_id=ctx.user_id, query=payload.get("query", ""))

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
