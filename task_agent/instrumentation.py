"""
task_agent/instrumentation.py

Sets up Arize Phoenix tracing for this agent, using Phoenix Cloud
(Arize's hosted version of Phoenix — same product, same tracing engine,
just without needing a local server).
"""

import os
from dotenv import load_dotenv
from phoenix.otel import register
from openinference.instrumentation.google_adk import GoogleADKInstrumentor

load_dotenv()

tracer_provider = register(
    project_name="astranova-task-agent",
    endpoint=os.environ.get("PHOENIX_COLLECTOR_ENDPOINT"),
    auto_instrument=False,
)

GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)

print("Phoenix tracing initialized (Arize Phoenix Cloud).")