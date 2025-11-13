# Developer: Anita Quevedo - anitaquevedo@google.com
# Equipo PE - LATAM
# Codigo adaptable de: https://github.com/google/adk-samples/blob/main/python/agents/data-science



import logging
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool
from .sub_agents import  analytics_agent

logger = logging.getLogger(__name__)

async def call_analytics_agent(
    question: str,
    tool_context: ToolContext,
):
    """
    This tool can generate Python code to process and analyze a dataset.

    Some of the tasks it can do in Python include:
    * Creating graphics for data visualization;
    * Processing or filtering existing datasets;
    * Combining datasets to create a joined dataset for further analysis.

    The Python modules available to it are:
    * io
    * math
    * re
    * matplotlib.pyplot
    * numpy
    * pandas

    The tool DOES NOT have the ability to retrieve additional data from
    a database. Only the data already retrieved will be analyzed.

    Args:
        question (str): Natural language question or analytics request.
        tool_context (ToolContext): The tool context to use for generating the
            SQL query.

    Returns:
        Response from the analytics agent.

    """
    logger.debug("call_analytics_agent: %s", question)

    bigquery_data = ""
    alloydb_data = ""

    if "bigquery_query_result" in tool_context.state:
        bigquery_data = tool_context.state["bigquery_query_result"]

    question_with_data = f"""
    Question to answer: {question}

    Actual data to analyze this question is available in the following data
    tables:

    <BIGQUERY>
    {bigquery_data}
    </BIGQUERY>


  """

    agent_tool = AgentTool(agent=analytics_agent)

    analytics_agent_output = await agent_tool.run_async(
        args={"request": question_with_data}, tool_context=tool_context
    )
    tool_context.state["analytics_agent_output"] = analytics_agent_output
    return analytics_agent_output