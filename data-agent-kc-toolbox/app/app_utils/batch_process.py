import asyncio
import json
import logging
import os
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import credentials

logging.basicConfig(level=logging.INFO)

# Get local credentials
creds, _ = google.auth.default()
if not creds.token:
  creds.refresh(Request())

# Mock auth_utils.get_user_credentials to use local credentials
from app import auth_utils


def mock_get_user_credentials(tool_context):
  return creds


auth_utils.get_user_credentials = mock_get_user_credentials

from app.ca_toolbox_engine_app import agent_engine

agent_engine.set_up()

questions = [
    "How's the New Accounts performance on Feb 27th, 2026?",
]


async def main():
  agent = agent_engine
  user_id = "eval_user"

  # Create directory for logs if it doesn't exist
  logs_dir = "app/app_utils/eval_logs"
  os.makedirs(logs_dir, exist_ok=True)

  for i, q in enumerate(questions, 1):
    logging.info(f"\nQuestion {i}: {q}")
    log_file_path = os.path.join(logs_dir, f"question_{i}.log")

    try:
      with open(log_file_path, "w") as f:
        f.write(f"Question {i}: {q}\n")
        f.write("-" * 40 + "\n")

        # Query the agent using async_stream_query
        response_parts = []
        async for event in agent.async_stream_query(user_id=user_id, message=q):
          logging.info(f"Raw event: {event}")
          # Write raw event to file
          f.write(f"Event: {json.dumps(event, indent=2)}\n")
          f.write("-" * 20 + "\n")

          for part in event.get("content", {}).get("parts", []):
            if "text" in part:
              response_parts.append(part["text"])

        response = "".join(response_parts)
        logging.info(f"Response {i}: {response}")

        f.write(f"Final Response:\n{response}\n")

    except Exception as e:
      logging.error(f"Failed to get response for question {i}: {e}")
      with open(log_file_path, "a") as f:
        f.write(f"Error: {e}\n")


if __name__ == "__main__":
  asyncio.run(main())
