import uuid
import json
import logging
from pprint import pprint

from dotenv import load_dotenv
load_dotenv(override=True)

# Import compiled LangGraph app (workflow is assembled in graph/workflow.py).
from backend.src.graph.workflow import app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
logger = logging.getLogger("clearstreamai")

def run_cli_simulation():
    '''
    Simulates the video compliance audit workflow using CLI input.
    '''

    # Session id helps correlate logs and outputs for a single execution run.
    session_id = str(uuid.uuid4())
    logger.info(f"Starting audit session with ID: {session_id}")

    # Initial state payload passed to LangGraph.
    # Downstream nodes enrich this with transcript, OCR, and compliance results.
    initial_inputs= {
        "video_url": "https://youtu.be/gj_QyeHTBiIQ",
        "video_id" : f"vid_{session_id[:8]}",
        "compliance_results" : [],
        "errors": []
    }

    print("n-----Initializing Workflow-----")
    print(f"Initial payload : {json.dumps(initial_inputs, indent=2)}")

    try:
        # Graph invocation executes node sequence and returns final merged state.
        final_state = app.invoke(initial_inputs)
        print("\n-----Workflow Completed-----")

        print("\n-----Compliance Audit Report-----")
        print(f"Video ID: {final_state.get('video_id')}")
        print(f"Status: {final_state.get('final_status')}")
        print("\n [VIOLATIONS DETECTED]")
        results = final_state.get('compliance_results', [])
        if results:
            for issue in results:
                print(f"- [{issue.get('severity')}] {issue.get('category')}: {issue.get('description')}")
        else:
            print("No violations detected. The video is compliant.")
        print("\n[FINAL SUMMARY]")
        print(final_state.get('final_report'))

    except Exception as e:
        # Bubble up after logging so calling environments can handle failure semantics.
        logger.error(f"Workflow Execution Failed: {str(e)}")
        raise e

if __name__ == "__main__":
    run_cli_simulation()