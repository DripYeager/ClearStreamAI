from langgraph.graph import StateGraph, END

from backend.src.graph.nodes import index_video_node, audit_content_node
from backend.src.graph.state import VideoAuditState

def create_graph():
    '''
    Constructs and compiles the LangGraph workflow for video audit
    Returns: Compiled graph: Runnable graph object for execution
    '''

    workflow= StateGraph(VideoAuditState)

    workflow.add_node("index_video", index_video_node)
    workflow.add_node("audit_content", audit_content_node)

    workflow.set_entry_point("index_video")
    workflow.add_edge("index_video", "audit_content")
    workflow.add_edge("audit_content", END)

    app= workflow.compile()
    return app

app= create_graph()