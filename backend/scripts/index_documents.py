import os
import glob
import logging
from dotenv import load_dotenv
load_dotenv(override=True)

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger= logging.getLogger("indexer")

def index_docs():
    '''
    Read documents chunk them and and upload to Azure AI Search
    '''

    current_dir= os.path.dirname(os.path.abspath(__file__))
    # Data folder is resolved relative to this script to keep execution location-agnostic.
    data_folder= os.path.join(current_dir, "../../backend/data")

    # Startup diagnostics: helps quickly validate runtime wiring in CI/local environments.
    logger.info("=" * 60)
    logger.info("Environment Configuration Check:")
    logger.info(f"AZURE_OPENAI_ENDPOINT: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    logger.info(f"AZURE_OPENAI_API_VERSION: {os.getenv('AZURE_OPENAI_API_VERSION')}")
    logger.info(f"Embedding Deployment: {os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 
                                                   'text-embedding-3-small')}")
    logger.info(f"AZURE_SEARCH_ENDPOINT: {os.getenv('AZURE_SEARCH_ENDPOINT')}")
    logger.info(f"AZURE_SEARCH_INDEX_NAME: {os.getenv('AZURE_SEARCH_INDEX_NAME')}")
    logger.info("=" * 60)

    required_vars= [
        'AZURE_OPENAI_ENDPOINT',
        'AZURE_OPENAI_API_KEY',
        'AZURE_SEARCH_ENDPOINT',
        'AZURE_SEARCH_INDEX_NAME',
        'AZURE_SEARCH_API_KEY'
    ]

    # Fail fast before any network calls if required secrets/config are missing.
    missing_vars= [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)} please check your .env file")
        return

    try:
        logger.info("Initializing Azure OpenAI Embeddings...")
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment=os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        )
        logger.info("Embeddings model initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize embeddings: {e}")
        logger.error("Please verify your Azure OpenAI deployment name and endpoint.")
        return

    try:
        # Vector store client targets an existing Azure Search index.
        logger.info("Initializing Azure AI Search vector store...")
        index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
        vector_store = AzureSearch(
            azure_search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
            azure_search_key=os.getenv("AZURE_SEARCH_API_KEY"),
            index_name=index_name,
            embedding_function=embeddings.embed_query
        )
        logger.info(f"✓ Vector store initialized for index: {index_name}")
    except Exception as e:
        logger.error(f"Failed to initialize Azure Search: {e}")
        logger.error("Please verify your Azure Search endpoint, API key, and index name.")
        return

    # Batch ingest all PDFs from the project data directory.
    pdf_files= glob.glob(os.path.join(data_folder, "*.pdf"))
    if not pdf_files:
        logger.warning("No PDF files found in the data folder. Please add some PDF documents to the data folder.")
    logger.info(f"Found {len(pdf_files)} PDF files to process: {[os.path.basename(f) for f in pdf_files]}")

    all_splits= []

    for pdf_path in pdf_files:
        try:
            logger.info(f"Loading PDF: {os.path.basename(pdf_path)}...")
            loader= PyPDFLoader(pdf_path)
            raw_docs= loader.load()

            # Chunking balances retrieval quality with token/cost constraints for embeddings.
            text_splitter= RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
            )
            splits= text_splitter.split_documents(raw_docs)
            # Normalize source metadata for traceability in audit responses.
            for split in splits:
                split.metadata['source']= os.path.basename(pdf_path)

            all_splits.extend(splits)
            logger.info(f"Loaded {len(splits)} chunks from {os.path.basename(pdf_path)}")

        except Exception as e:
            logger.error(f"Error processing {os.path.basename(pdf_path)}: {e}")

        if all_splits:
            logger.info(f"Uploading {len(all_splits)} chunks to Azure AI Search '{index_name}'...")
            try:
                vector_store.add_documents(documents=all_splits)
                logger.info("="*60)
                logger.info(f"Successfully uploaded {len(all_splits)} chunks to Azure AI Search")
                logger.info("="*60)
            except Exception as e:
                logger.error(f"Error uploading to Azure AI Search: {e}")
                logger.error("Please check the Azure Search configuration and try again.")

        else:
            logger.warning("No documents were processed.")

if __name__ == "__main__":
    index_docs()