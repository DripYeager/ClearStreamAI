import operator
from typing import Annotated, List, Dict, Optional, Any, TypedDict

class ComplianceIssue(TypedDict):
    category: str
    description: str
    severity: str
    timestamp: Optional[str]

class VideoAuditState(TypedDict):
    '''
    Data schema for langgraph execution content
    '''
    video_id: str
    video_url: str

    local_file_path: str
    video_metadata: Dict[str, Any]
    transcript: Optional[str]
    ocr_text: Optional[str]

    compliance_results: Annotated[List[ComplianceIssue], operator.add]
    
    final_status: str
    final_report: str

    errors: Annotated[List[str], operator.add]