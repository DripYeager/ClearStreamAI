import operator
from typing import Annotated, List, Dict, Optional, Any, TypedDict

class ComplianceIssue(TypedDict):
    # Normalized issue structure expected from audit nodes and final reports.
    category: str
    description: str
    severity: str
    timestamp: Optional[str]

class VideoAuditState(TypedDict):
    '''
    Data schema for langgraph execution content
    '''
    # Input identifiers provided at invocation time.
    video_id: str
    video_url: str

    # Enriched artifacts produced during indexing/analysis.
    local_file_path: str
    video_metadata: Dict[str, Any]
    transcript: Optional[str]
    ocr_text: Optional[str]

    # Merge strategy for LangGraph: values from multiple node updates are appended.
    compliance_results: Annotated[List[ComplianceIssue], operator.add]
    
    # Final node-level outcome fields returned to clients.
    final_status: str
    final_report: str

    # Aggregated runtime errors across nodes for easier debugging.
    errors: Annotated[List[str], operator.add]