"""Verification Tool Agent for validating Dataplex entries contexts against questions."""

import json
import logging
import os
from typing import Any

from google import genai
from google.adk.tools.tool_context import ToolContext
import google.auth
from google.cloud import dataplex_v1

from . import auth_utils
from .dataplex_utils import get_detailed_context
from .file_utils import log_to_file

VERIFICATION_PROMPT_TEMPLATE = """
This is user question: {question}
Those are the entries we want to use:
{entry_names}
And this is all knowledge we have about these entries:
{context_block}

Can you answer this question using this knowledge? Short answer YES or NO. If no then tell what data is missing what should we search for. Keep the answer clean and concise.
If YES, then also provide a short summary of what you think has to be done to get the answer.
If NO, then only provide the missing information that is needed to answer the question.
Start your answer with YES or NO.
Keep the response up to 3000 characters.
"""


def verify_entries_for_question(
    entry_names: list[str], question: str, tool_context: ToolContext
) -> str:
  """Verifies if a set of entries can answer a question, fetching full info or LookupContext.

  Args:
      entry_names: List of full Dataplex resource names to verify.
      question: The original user query to validate against the context.
  """
  logging.info(
      f"Tool 'verify_entries_for_question' called for entries: {entry_names}"
  )
  try:
    creds = auth_utils.get_user_credentials(tool_context)
    client = dataplex_v1.CatalogServiceClient(credentials=creds)

    context_block = get_detailed_context(entry_names, client)

    # Use Gemini to verify
    prompt = VERIFICATION_PROMPT_TEMPLATE.format(
        question=question,
        entry_names=entry_names,
        context_block=context_block,
    )
    logging.info(
        "Total characters in prompt landing to LLM for verification:"
        f" {len(prompt)}"
    )

    log_to_file(prompt, "verify_entries_prompt")

    genai_client = genai.Client()
    gen_response = genai_client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt,
    )
    output = gen_response.text
    log_to_file(output, "verify_entries_response")
    return output
  except Exception as e:
    err_msg = f"Error in verify_entries_for_question: {e}"
    logging.error(err_msg)
    return err_msg
