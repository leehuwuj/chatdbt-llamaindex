from llama_index.core.agent import ReActAgent
from app.dbt.custom import dbt_react_formatter


def dbt_tools():
    """
    Returns a DBT tool.
    """
    from app.dbt import DbtToolSpec, DbtManifestToolSpec, DbtRunResultToolSpec
    from app.constants import DBT_PROJECT_DIR

    if DBT_PROJECT_DIR is None:
        raise ValueError("DBT_PROJECT_DIR is not set")

    basic_tools = DbtToolSpec(DBT_PROJECT_DIR).to_tool_list()

    manifest_tools = DbtManifestToolSpec(project_dir=DBT_PROJECT_DIR).to_tool_list()

    run_result_tools = DbtRunResultToolSpec(project_dir=DBT_PROJECT_DIR).to_tool_list()

    return basic_tools + manifest_tools + run_result_tools


def get_chat_engine():
    """
    Constructs an AgentRunner with the default LLM, a query engine tool, and additional tools from the environment.
    """
    tools = []

    # Add the query engine tool
    tools.append(get_query_engine_tool())

    tools += dbt_tools()

    return ReActAgent.from_tools(
        tools=tools, react_chat_formatter=dbt_react_formatter, verbose=True
    )
