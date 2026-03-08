import os
import logging
from azure.monitor.opentelemetry import configure_azure_monitor

logger= logging.getLogger("clearstreamai-telemetry")

def setup_telemetry():
    '''
    Configures Azure Monitor OpenTelemetry for tracing and logging.
    Tracks HTTP requests and errors, database queries, and LLM calls, performance metrics.
    '''
    try:
        # Telemetry is environment-driven: if connection string is absent,
        # application remains functional without exporting observability signals.
        connection_string= os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

        if not connection_string:
            logger.warning("APPLICATIONINSIGHTS_CONNECTION_STRING is not set. Telemetry will not be collected.")
            return
        
        try:
            # Register Azure Monitor exporters/instrumentation for this process.
            configure_azure_monitor(
                connection_string=connection_string,
                logger_name = "clearstreamai-telemetry",
            )
            logger.info("Azure Monitor OpenTelemetry initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Azure Monitor OpenTelemetry: {e}")
        