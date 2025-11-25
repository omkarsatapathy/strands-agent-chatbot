"""
Okkular Assistant - Agent Runtime Entrypoint

Main entrypoint for the conversational AI agent runtime.

Features:
- Memory-enabled conversations with context retrieval
- Full observability with OpenTelemetry and CloudWatch
- Session and user context propagation
- Circuit breakers for resilience
- Input validation and PII redaction
- Auto-generated tools from registry via Strands adapter

Architecture:
1. Load all tools from registry via StrandsAdapterFactory
2. Configure memory hooks for lifecycle management
3. Create Agent with Bedrock model, tools, and hooks
4. Handle invocation with session/actor context
5. Return response with full observability

TODO: Implement agent initialization and invocation handler
TODO: Configure memory hooks for context retrieval/storage
TODO: Add input validation and PII redaction
TODO: Add circuit breaker for Bedrock and Memory service calls
TODO: Configure OpenTelemetry for distributed tracing
"""

import json
import boto3
import time
from dotenv import load_dotenv
from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore import BedrockAgentCoreApp
from src.tools.adapters.strands_adapter import (
    lookup_products_tool,
    search_celebrity_style_tool,
    style_guide_tool,
    mcp_tool
)
from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session
from config.config_loader import get_config
from src.utils.tool_output_parser import tool_output
from src.hooks.MemoryHookWithLongTermMemoryRetrieve import MemoryHookProvider
from bedrock_agentcore.memory import MemoryClient
from strands.hooks import HookRegistry
from src.utils.logging import get_logger
from src.hooks import ToolOutputCaptureHook

logger = get_logger("stands")
config = get_config()

app = BedrockAgentCoreApp()

# Initialize memory client and hook
memory_client = MemoryClient(region_name=config.get("aws.region", "ap-southeast-2"))
memory_id = config.get("memory.memory_id", "okkular_memory")
memory_hook = MemoryHookProvider(memory_id, memory_client)

# Register hooks
hook_registry = HookRegistry()
memory_hook.register_hooks(hook_registry)

# Model configuration
MODEL_ID = config.get("model.model_id", "global.anthropic.claude-sonnet-4-5-20250929-v1:0")

# Initialize Bedrock Runtime client for image processing
bedrock_runtime = boto3.client(
    "bedrock-runtime",
    region_name=config.get("aws.region", "ap-southeast-2")
)

# Initialize the Bedrock model
model = BedrockModel(
    model_id=MODEL_ID,
    region_name=config.get("aws.region", "ap-southeast-2")
)

# Create tool output capture hook
tool_output_hook = ToolOutputCaptureHook()

agent = Agent(
    model=model,
    tools=[lookup_products_tool, search_celebrity_style_tool, style_guide_tool, mcp_tool],
    system_prompt=config.get("agent.system_prompts.okkular_assistant", ""),
    hooks=[memory_hook, tool_output_hook],
    state={"actor_id": None, "session_id": None},
    callback_handler=None
)

@app.entrypoint
def okkularplus_agent(payload):
    """Main agent handler for OkkularPlus"""
    print("Invoking OkkularPlus Agent with payload")
    user_input = payload.get("content")
    actor_id = payload.get("actor_id")
    session_id = payload.get("session_id")
    logger.info(f"Received payload: {payload}")

    # Set actor_id and session_id in agent state
    if actor_id:
        agent.state.set("actor_id", actor_id)
    if session_id:
        agent.state.set("session_id", session_id)

    if "image" in payload:
        img_link = payload.get("image")
        print(f"Image link: {img_link}")
        request_body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 20000,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": f"Please convert this image to a user query for the image in detail majorly focusing on the style, color, and texture of the image. Please provide the description in an elaborate query under 50 words.\n\n The image link is here:\n\n {img_link}"
            }
        ]
        })
        time1 = time.time()
        response = bedrock_runtime.invoke_model(
                    modelId=MODEL_ID,
                    body=request_body
        )
        time2 = time.time()
        print(f"Time taken to get image description: {time2 - time1}\n\n")

        # Parse the streaming response body
        response_body = json.loads(response["body"].read())
        img_desc = response_body["content"][0]["text"]

        print(f"\n\nImage description: {img_desc} \n\n")

        user_input = f"Here is a the description of the image which is attached by the user in chat box:\n\n {img_desc}. \n \n And here is the user query:\n\n {user_input}"


    # Clear previous tool outputs before new execution
    tool_output_hook.clear()
    logger.info(f"Cleared tool_output before execution - ID: {id(tool_output)}")

    response = agent(user_input)
    # logger.info(f"Agent response: {response}")

    # Get captured tool outputs from hook
    captured_outputs = tool_output_hook.get_outputs()
    logger.info(f"Captured {len(captured_outputs)} tool outputs via hook")
    logger.debug(f"Tool outputs: {captured_outputs}")

    # Extract metadata and web_search from the tool output
    metadata_list = []
    web_search_urls = []

    try:
        # Extract metadata from the tool output - this contains the structured product info
        tool_data = captured_outputs[0]['data']
        metadata_list = tool_data.get('metadata', [])
        web_search_urls = tool_data.get('web_search', [])
    except (IndexError, KeyError, TypeError) as e:
        logger.warning(f"Failed to extract data from tool output: {e}, using empty lists")
        metadata_list = []
        web_search_urls = []

    output = {
        "body": {
            "textResponse": response.message['content'][0]['text'],
            "products": metadata_list,
            "web_search": web_search_urls
        }
    }
    logger.info(f"Final output with {len(metadata_list)} tool outputs")

    return output

if __name__ == "__main__":
    app.run()