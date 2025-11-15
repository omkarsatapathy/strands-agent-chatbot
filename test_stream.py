import asyncio
from strands import Agent
from strands.models.llamacpp import LlamaCppModel
from src.config import Config

async def test():
    model = LlamaCppModel(
        base_url=Config.LLAMA_CPP_URL,
        model_id="default",
        params={"max_tokens": 500, "temperature": 0.7}
    )

    agent = Agent(model=model, system_prompt="You are helpful")

    print("=== Testing stream_async ===")
    async for event in agent.stream_async("Say hello"):
        if isinstance(event, dict):
            if 'event' in event:
                inner = event['event']
                if 'contentBlockDelta' in inner:
                    print(f"DELTA: {inner['contentBlockDelta']}")
            if 'message' in event:
                print(f"MESSAGE: {event['message']}")

    print("\n=== Testing invoke_async ===")
    response = await agent.invoke_async("Say hello")
    print(f"RESPONSE TYPE: {type(response)}")
    print(f"RESPONSE STR: {str(response)}")

asyncio.run(test())
