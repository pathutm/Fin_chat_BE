import os
import sys
import asyncio
from dotenv import load_dotenv

os.environ["NEMOGUARDRAILS_LLM_FRAMEWORK"] = "langchain"

from nemoguardrails import RailsConfig, LLMRails

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

config_path = os.path.dirname(__file__)
config = RailsConfig.from_path(config_path)
rails = LLMRails(config)


async def check_input_guardrail(user_message: str):
    """Check user input against the Guardrails."""
    result = await rails.check_async([
        {
            "role": "user",
            "content": user_message
        }
    ])
    return result


async def main():
    # Uses command line argument if provided, otherwise defaults to sample input
    user_input = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is my current salary?"
    print(f"Testing Guardrail on input: \"{user_input}\"")

    result = await check_input_guardrail(user_input)
    print("Result:", result)


if __name__ == "__main__":
    asyncio.run(main())