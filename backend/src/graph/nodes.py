import json
import os
import logging
import re
from typing import Any, Dict, List

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

from backend.src.graph.state import VideoAuditState, ComplianceIssue

from backend.src.services.video_indexer import VideoIndexerService

logger = logging.getLogger("clearstreamai")
logging.basicConfig(level=logging.INFO)

def index_video_node(state: VideoAuditState) -> Dict[str, Any]:
    '''
    Download the video from url and uploads to Azure video indexer
    Extracts the insight
    ''''
    video_url = state.get('video_url')
    video_id_input= state.get('video_id','vid_demo')

    logger.info(f"----[Node: indexer] Processing : {video_url}")

    # Local temporary file used only for upload, then deleted to avoid disk buildup.
    local_filename= "temp_audit_video.mp4"

    try:
        # This node is intentionally strict about accepted sources to keep ingestion predictable.
        vi_service= VideoIndexerService()
        if "youtube.com" in video_url or "youtu.be" in video_url:
            local_path= vi_service.download_youtube_video(video_url, output_path=local_filename)
        else:
            raise Exception(f"Please provide a valid video url")

        azure_video_id= vi_service.upload_video(local_path, video_name=video_id_input)
        logger.info(f"Upload successful. Azure video id: {azure_video_id}")

        if os.path.exists(local_path):
            os.remove(local_path)

        # Wait for Azure indexing to finish before extracting normalized state fields
        # that downstream graph nodes consume (transcript, OCR, metadata, etc.).
        raw_insights= vi_service.wait_for_video_processing(azure_video_id)
        clean_data= vi_service.extract_data(raw_insights)
        logger.info(f"----[Node: indexer] Extraction Completed")
        return clean_data
    except Exception as e:
        logger.error(f"Error indexing video: {e}")
        return {
            'errors': [str(e)],
            'final_status': 'Fail',
            'transcript': "",
            'ocr_text': []
        }

def audio_content_node(state: VideoAuditState) -> Dict[str, Any]:
    '''
    Perform Retrival Augmented Generation to audit the audio content of the video
    '''
    logger.info(f"----[Node: Audior] Querying knowledge base and LLM")

    transcript= state.get('transcript',"")
    if not transcript:
        logger.warning("No transcript found. Skipping audio content audit.")
        return {
            "final_status": "Fail",
            "final_report": "No transcript found. Skipping audio content audit.",
        }

    #initialize LLM and embedding model
    llm= AzureChatOpenAI(
        azure_deployment=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        temperature=0.0,
    )
    
    embeddings= AzureOpenAIEmbeddings(
        azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
        openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )

    # Azure AI Search provides regulation context for RAG grounding.
    # Using env vars keeps deployment-specific values out of code.
    vector_store= AzureSearch(
        azure_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        azure_search_key=os.getenv("AZURE_SEARCH_API_KEY"),
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
        embedding_function=embeddings.embed_query
    )

    ocr_text= state.get('ocr_text',[])
    # Combine spoken transcript + on-screen text so retrieval reflects full ad content.
    query_text= f"{transcript} {''.join(ocr_text)}"
    docs= vector_store.similarity_search(query_text, k=3)
    retrieved_rules= "\n\n".join([doc.page_content for doc in docs])

    # Prompt contract: model must return machine-parseable JSON with
    # compliance_results, status, and final_report for deterministic state updates.
    system_prompt = f"""
    You are a senior brand compliance auditor.

    OFFICIAL Regulatory Rules:
    {retrieved_rules}

    Instructions:
    1. Analyze the transcript and OCR text to identify any compliance issues.
    2. If a compliance issue is identified, return strictly the issue in the following format:

    {{
        "compliance_results": [
            {{
                "category": "Claim Validation",
                "severity": "CRITICAL",
                "description": "Explanation of the violation..."
            }}
        ],
        "status": "FAIL", 
        "final_report": "Summary of findings..."
    }}

    If no violations are found, set "status" to "PASS" and "compliance_results" to [].
    """

    user_message= f"""
        Video_Metadata: {state.get('video_metadata',{})}
        Transcript: {transcript}
        ON-Screen Text: {ocr_text}
        """

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])
        
        content = response.content
        # Handle fenced JSON responses from LLMs before parsing.
        if "```" in content:
            content = re.search(r"```(?:json)?(.*?)```", content, re.DOTALL).group(1)
            
        audit_data = json.loads(content.strip())
        
        return {
            "compliance_results": audit_data.get("compliance_results", []),
            "final_status": audit_data.get("status", "FAIL"),
            "final_report": audit_data.get("final_report", "No report generated.")
        }

    except Exception as e:
        logger.error(f"System Error in Auditor Node: {str(e)}")
        logger.error(f"Raw LLM Response: {response.content if 'response' in locals() else 'None'}")
        return {
            "errors": [str(e)],
            "final_status": "FAIL"
        }