from langgraph.graph import StateGraph, END

from backend.src.graph.nodes import index_video_node, audit_content_node
from backend.src.graph.state import VideoAuditState

def create_graph():
    '''
    Constructs and compiles the LangGraph workflow for video audit
    Returns: Compiled graph: Runnable graph object for execution
    '''

    # Shared state contract for all nodes in this pipeline.
    # Each node reads/writes keys from VideoAuditState as it progresses.
    workflow= StateGraph(VideoAuditState)

    # Node registration defines the callable units in execution order.
    workflow.add_node("index_video", index_video_node)
    workflow.add_node("audit_content", audit_content_node)

    # Entry point starts with ingestion/indexing, then moves to compliance audit.
    workflow.set_entry_point("index_video")
    workflow.add_edge("index_video", "audit_content")
    # Explicit terminal edge marks successful completion of the graph run.
    workflow.add_edge("audit_content", END)

    # Compiled app is the runnable graph object used by callers.
    app= workflow.compile()
    return app

# Module-level graph instance to avoid recompiling on each import/use.
app= create_graph()