import uuid
import logging
from fastapi import FastAPI, HTTPException

from pydantic import BaseModel
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv(override=True)

from backend.src.api.telemetry import setup_telemetry
# Initialize telemetry at startup so request traces and errors are exported early.
setup_telemetry()


from backend.src.graph.workflow import app as compliance_graph

logging.basicConfig(level=logging.INFO)

logger= logging.getLogger("clearstreamai-api-server")

app = FastAPI(
    title="Clearstream AI Video Compliance API",
    description="API for video compliance audit workflow",
    version="1.0.0"
)

class AuditRequest(BaseModel):
    '''
    Define the expected structure of incoming API requests.
    '''
    video_url: str

class ComplianceIssue(BaseModel):
    # Response schema mirrors graph output shape for client-side consistency.
    category: str
    severity: str
    description: str

class AuditResponse(BaseModel):
    session_id: str
    video_id: str
    status: str
    final_report: str
    compliance_results: List[ComplianceIssue]

@app.post("/audit", response_model=AuditResponse)
async def audit_video(request: AuditRequest):
    '''
    API endpoint for video compliance audit workflow.
    '''
    # Session identifier is generated per request for traceability in logs/telemetry.
    session_id = str(uuid.uuid4())
    video_id_input= f"vid_{session_id[:8]}"
    logger.info(f"Recieved the Audit Request for Video: {request.video_url} session id: {session_id}")

    # Initial graph state; downstream nodes enrich this with extracted content
    # and compliance findings.
    initial_inputs= {
        "video_url": request.video_url,
        "video_id": video_id_input,
        "compliance_results": [],
        "errors": []
    }

    try:
        # Graph invocation is synchronous here; FastAPI worker waits for completion.
        final_state = compliance_graph.invoke(initial_inputs)
        return AuditResponse(
            session_id=session_id,
            video_id=final_state.get('video_id'),
            status=final_state.get('final_status', 'UNKNOWN'),
            final_report=final_state.get('final_report', 'No report generated.'),
            compliance_results=final_state.get('compliance_results', [])
        )
    except Exception as e:
        # Return sanitized HTTP 500 while preserving detailed server-side logs.
        logger.error(f"Audit Workflow Failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Audit Workflow Failed: {str(e)}")

@app.get("/health")
async def health_check():
    '''
    Health check endpoint to verify API is running.
    '''
    return {"status": "ok", "service": "clearstreamai-api-server"}        