# BUSINESS SCIENCE UNIVERSITY
# AI DATA SCIENCE TEAM
# ***
# * ML Agents: Survival Analysis Agent

from typing_extensions import TypedDict, Annotated, Sequence
import operator

from langchain_core.prompts import PromptTemplate
from langchain_core.messages import BaseMessage
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Checkpointer

import os
import json
import pandas as pd

from IPython.display import Markdown

from ai_data_science_team.templates import (
    node_func_human_review,
    node_func_fix_agent_code,
    node_func_report_agent_outputs,
    create_coding_agent_graph,
    BaseAgent,
)
from ai_data_science_team.parsers.parsers import PythonOutputParser
from ai_data_science_team.utils.regex import (
    relocate_imports_inside_function,
    add_comments_to_top,
    format_agent_name,
    format_recommended_steps,
    get_generic_summary,
)
from ai_data_science_team.tools.survival import (
    get_survival_data_summary,
    validate_survival_data,
    get_survival_analysis_best_practices,
)
from ai_data_science_team.utils.logging import log_ai_function, log_ai_error
from ai_data_science_team.utils.sandbox import run_code_sandboxed_subprocess
from ai_data_science_team.utils.messages import get_last_user_message_content

# Setup
AGENT_NAME = "survival_analysis_agent"
LOG_PATH = os.path.join(os.getcwd(), "logs/")


class SurvivalAnalysisAgent(BaseAgent):
    """
    Creates a survival analysis agent for analyzing time-to-event data in cancer research
    and other medical applications. The agent can perform Kaplan-Meier analysis, Cox
    proportional hazards modeling, risk stratification, and survival predictions.

    This agent is specifically designed for oncology research where survival analysis is
    critical for:
    - Patient survival time analysis
    - Treatment efficacy comparison
    - Prognostic factor identification
    - Risk stratification
    - Clinical trial outcomes

    Parameters
    ----------
    model : langchain.llms.base.LLM
        The language model used to generate the survival analysis function.
    time_column : str
        Name of the column containing time-to-event data.
    event_column : str
        Name of the column containing event indicators (1=event, 0=censored).
    n_samples : int, optional
        Number of samples used when summarizing the dataset. Defaults to 30.
    log : bool, optional
        Whether to log the generated code and errors. Defaults to False.
    log_path : str, optional
        Directory path for storing log files. Defaults to None.
    file_name : str, optional
        Name of the file for saving the generated response. Defaults to "survival_analyzer.py".
    function_name : str, optional
        Name of the generated survival analysis function. Defaults to "survival_analyzer".
    overwrite : bool, optional
        Whether to overwrite the log file if it exists. Defaults to True.
    human_in_the_loop : bool, optional
        Enables user review of analysis instructions. Defaults to False.
    bypass_recommended_steps : bool, optional
        If True, skips the default recommended analysis steps. Defaults to False.
    bypass_explain_code : bool, optional
        If True, skips the step that provides code explanations. Defaults to False.
    checkpointer : langgraph.types.Checkpointer, optional
        Checkpointer to save and load the agent's state. Defaults to None.

    Methods
    -------
    invoke_agent(user_instructions: str, data_raw: pd.DataFrame, max_retries=3, retry_count=0)
        Performs survival analysis on the provided dataset based on user instructions.
    get_survival_results()
        Retrieves the survival analysis results as a pandas DataFrame.
    get_plotly_graph()
        Retrieves the generated survival curve as a Plotly graph object.
    get_survival_analyzer_function()
        Retrieves the generated Python function used for survival analysis.

    Examples
    --------
    ```python
    import pandas as pd
    from langchain_openai import ChatOpenAI
    from ai_data_science_team.ml_agents import SurvivalAnalysisAgent

    llm = ChatOpenAI(model="gpt-4o-mini")

    # Create survival analysis agent
    survival_agent = SurvivalAnalysisAgent(
        model=llm,
        time_column="survival_time",
        event_column="death_event",
        log=True,
        log_path="logs/"
    )

    # Load cancer patient data
    df = pd.read_csv("cancer_patient_data.csv")

    # Perform Kaplan-Meier analysis
    survival_agent.invoke_agent(
        user_instructions="Create Kaplan-Meier survival curves stratified by treatment group",
        data_raw=df,
        max_retries=3,
        retry_count=0
    )

    # Get results
    survival_results = survival_agent.get_survival_results()
    survival_plot = survival_agent.get_plotly_graph()
    ```

    Returns
    --------
    SurvivalAnalysisAgent : langchain.graphs.CompiledStateGraph
        A survival analysis agent implemented as a compiled state graph.
    """

    def __init__(
        self,
        model,
        time_column: str,
        event_column: str,
        n_samples=30,
        log=False,
        log_path=None,
        file_name="survival_analyzer.py",
        function_name="survival_analyzer",
        overwrite=True,
        human_in_the_loop=False,
        bypass_recommended_steps=False,
        bypass_explain_code=False,
        checkpointer: Checkpointer = None,
    ):
        self._params = {
            "model": model,
            "time_column": time_column,
            "event_column": event_column,
            "n_samples": n_samples,
            "log": log,
            "log_path": log_path,
            "file_name": file_name,
            "function_name": function_name,
            "overwrite": overwrite,
            "human_in_the_loop": human_in_the_loop,
            "bypass_recommended_steps": bypass_recommended_steps,
            "bypass_explain_code": bypass_explain_code,
            "checkpointer": checkpointer,
        }
        self._compiled_graph = self._make_compiled_graph()
        self.response = None

    def invoke_agent(
        self,
        data_raw: pd.DataFrame,
        user_instructions: str = None,
        max_retries: int = 3,
        retry_count: int = 0,
        **kwargs,
    ):
        """
        Invokes the agent. Returns the response and stores it in the response attribute.
        """
        self.response = self.invoke(
            {
                "messages": [("user", user_instructions)] if user_instructions else [],
                "user_instructions": user_instructions,
                "data_raw": data_raw.to_dict(),
                "max_retries": max_retries,
                "retry_count": retry_count,
            },
            **kwargs,
        )
        return None

    async def ainvoke_agent(
        self,
        data_raw: pd.DataFrame,
        user_instructions: str = None,
        max_retries: int = 3,
        retry_count: int = 0,
        **kwargs,
    ):
        """
        Asynchronously invokes the agent.
        """
        self.response = await self.ainvoke(
            {
                "messages": [("user", user_instructions)] if user_instructions else [],
                "user_instructions": user_instructions,
                "data_raw": data_raw.to_dict(),
                "max_retries": max_retries,
                "retry_count": retry_count,
            },
            **kwargs,
        )
        return None

    def invoke_messages(
        self,
        messages: Sequence[BaseMessage],
        data_raw: pd.DataFrame,
        max_retries: int = 3,
        retry_count: int = 0,
        **kwargs,
    ):
        """
        Invokes the agent with an explicit message list (preferred for supervisors/teams).
        """
        user_instructions = kwargs.pop("user_instructions", None)
        if user_instructions is None:
            user_instructions = get_last_user_message_content(messages)
        self.response = self.invoke(
            {
                "messages": messages,
                "user_instructions": user_instructions,
                "data_raw": data_raw.to_dict(),
                "max_retries": max_retries,
                "retry_count": retry_count,
            },
            **kwargs,
        )
        return None

    def _make_compiled_graph(self):
        """
        Create the compiled graph for the survival analysis agent.
        """
        self.response = None
        return make_survival_analysis_agent(**self._params)

    def get_survival_results(self):
        """
        Retrieves the survival analysis results.
        """
        if self.response:
            return pd.DataFrame(self.response.get("survival_results"))

    def get_plotly_graph(self):
        """
        Retrieves the Plotly graph if one was generated.
        """
        if self.response and self.response.get("plotly_graph"):
            try:
                import plotly.graph_objects as go

                return go.Figure(self.response.get("plotly_graph"))
            except ImportError:
                print("Plotly not installed. Install with: pip install plotly")
                return None

    def get_survival_analyzer_function(self, markdown=False):
        """
        Retrieves the agent's survival analysis function.
        """
        if self.response:
            if markdown:
                return Markdown(
                    f"```python\n{self.response.get('survival_analyzer_function')}\n```"
                )
            else:
                return self.response.get("survival_analyzer_function")

    def get_recommended_analysis_steps(self, markdown=False):
        """
        Retrieves the agent's recommended analysis steps.
        """
        if self.response:
            if markdown:
                return Markdown(self.response.get("recommended_steps"))
            else:
                return self.response.get("recommended_steps")


def make_survival_analysis_agent(
    model,
    time_column: str,
    event_column: str,
    n_samples=30,
    log=False,
    log_path=None,
    file_name="survival_analyzer.py",
    function_name="survival_analyzer",
    overwrite=True,
    human_in_the_loop=False,
    bypass_recommended_steps=False,
    bypass_explain_code=False,
    checkpointer: Checkpointer = None,
):
    """
    Creates a survival analysis agent for time-to-event data analysis.

    The agent performs survival analysis including:
    - Kaplan-Meier survival curves
    - Cox proportional hazards regression
    - Risk stratification
    - Group comparisons (log-rank test)
    - Survival predictions

    Parameters
    ----------
    model : langchain.llms.base.LLM
        The language model to use to generate code.
    time_column : str
        Name of the column containing time-to-event data.
    event_column : str
        Name of the column containing event indicators (1=event, 0=censored).
    n_samples : int, optional
        The number of samples to use when summarizing the dataset. Defaults to 30.
    log : bool, optional
        Whether or not to log the code generated. Defaults to False.
    log_path : str, optional
        The path to the directory where the log files should be stored.
    file_name : str, optional
        The name of the file to save the response to.
    function_name : str, optional
        The name of the function that will be generated.
    overwrite : bool, optional
        Whether or not to overwrite the log file if it already exists.
    human_in_the_loop : bool, optional
        Whether or not to use human in the loop. Defaults to False.
    bypass_recommended_steps : bool, optional
        Bypass the recommendation step. Defaults to False.
    bypass_explain_code : bool, optional
        Bypass the code explanation step. Defaults to False.
    checkpointer : langgraph.types.Checkpointer, optional
        Checkpointer to save and load the agent's state.

    Returns
    -------
    app : langchain.graphs.CompiledStateGraph
        The survival analysis agent as a state graph.
    """
    llm = model

    DEFAULT_ANALYSIS_STEPS = format_recommended_steps(
        """
1. Validate survival data (time column non-negative, event column binary).
2. Generate Kaplan-Meier survival curves with confidence intervals.
3. Perform group comparisons using log-rank test if stratification variable is specified.
4. Fit Cox proportional hazards model if covariates are provided.
5. Calculate risk scores and stratify patients into risk groups.
6. Create interactive Plotly visualizations of survival curves.
7. Return summary statistics including median survival times and hazard ratios.
        """,
        heading="# Recommended Survival Analysis Steps:",
    )

    best_practices = get_survival_analysis_best_practices()

    def _summarize_survival_data(df: pd.DataFrame) -> str:
        """Summarize survival data for prompts."""
        return get_survival_data_summary(
            df, time_column, event_column, n_sample=min(n_samples, 10)
        )

    if human_in_the_loop:
        if checkpointer is None:
            print("Human in the loop enabled. Setting checkpointer to MemorySaver().")
            checkpointer = MemorySaver()

    if bypass_recommended_steps and human_in_the_loop:
        bypass_recommended_steps = False
        print("Bypass recommended steps set to False to enable human in the loop.")

    if log:
        if log_path is None:
            log_path = LOG_PATH
        if not os.path.exists(log_path):
            os.makedirs(log_path)

    # Define GraphState
    class GraphState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], operator.add]
        user_instructions: str
        recommended_steps: str
        data_raw: dict
        survival_results: dict
        plotly_graph: dict
        data_summary: str
        survival_analyzer_function: str
        survival_analyzer_function_path: str
        survival_analyzer_file_name: str
        survival_analyzer_function_name: str
        survival_analyzer_error: str
        survival_analyzer_error_log_path: str
        max_retries: int
        retry_count: int

    def recommend_analysis_steps(state: GraphState):
        """Recommend survival analysis steps based on the data."""
        print(format_agent_name(AGENT_NAME))
        print("    * RECOMMEND SURVIVAL ANALYSIS STEPS")

        recommend_steps_prompt = PromptTemplate(
            template="""
            You are a Survival Analysis Expert specializing in cancer research and clinical outcomes.
            Given the following survival data, recommend a series of numbered analysis steps.

            The steps should be tailored to the data characteristics and user requirements.

            General Survival Analysis Steps:

            * Validate data (time non-negative, event binary)
            * Kaplan-Meier survival curves
            * Log-rank test for group comparisons
            * Cox proportional hazards modeling
            * Risk stratification and scoring
            * Visualization with confidence intervals
            * Summary statistics (median survival, hazard ratios)

            Custom Steps:
            * Analyze the data structure to determine appropriate analyses
            * Consider covariates for multivariate Cox regression
            * Identify stratification variables for subgroup analysis
            * Recommend appropriate visualization strategies

            IMPORTANT:
            Take into account user instructions that may specify particular analyses or modifications.
            Include comments explaining your reasoning for each step.

            User instructions:
            {user_instructions}

            Previously Recommended Steps (if any):
            {recommended_steps}

            Survival Data Summary:
            {data_summary}

            Return steps as a numbered list. You can include short code snippets for clarity,
            but do not provide a complete implementation. The code will be generated separately.

            Best Practices to Consider:
            {best_practices}
            """,
            input_variables=[
                "user_instructions",
                "recommended_steps",
                "data_summary",
                "best_practices",
            ],
        )

        data_raw = state.get("data_raw")
        df = pd.DataFrame.from_dict(data_raw)

        # Validate survival data
        is_valid, issues = validate_survival_data(df, time_column, event_column)
        if not is_valid:
            error_msg = "Survival data validation failed:\n" + "\n".join(issues)
            print(f"      ERROR: {error_msg}")

        data_summary_str = _summarize_survival_data(df)

        steps_agent = recommend_steps_prompt | llm
        recommended_steps = steps_agent.invoke(
            {
                "user_instructions": state.get("user_instructions"),
                "recommended_steps": state.get("recommended_steps"),
                "data_summary": data_summary_str,
                "best_practices": best_practices,
            }
        )

        return {
            "recommended_steps": format_recommended_steps(
                recommended_steps.content.strip(),
                heading="# Recommended Survival Analysis Steps:",
            ),
            "data_summary": data_summary_str,
        }

    def create_survival_analyzer_code(state: GraphState):
        print("    * CREATE SURVIVAL ANALYZER CODE")

        if bypass_recommended_steps:
            print(format_agent_name(AGENT_NAME))
            data_raw = state.get("data_raw")
            df = pd.DataFrame.from_dict(data_raw)
            data_summary_str = _summarize_survival_data(df)
            steps_for_prompt = DEFAULT_ANALYSIS_STEPS
        else:
            data_summary_str = state.get("data_summary")
            steps_for_prompt = state.get("recommended_steps") or DEFAULT_ANALYSIS_STEPS

        survival_analysis_prompt = PromptTemplate(
            template="""
            You are a Survival Analysis Agent. Create a {function_name}() function that performs
            survival analysis on the provided data following these recommended steps.

            Recommended Steps:
            {recommended_steps}

            You can use these libraries for survival analysis:
            - lifelines: For Kaplan-Meier and Cox regression
            - pandas, numpy: For data manipulation
            - plotly.graph_objects: For interactive survival curve plots
            - scikit-learn: For additional modeling if needed

            Survival Data Summary:
            {data_summary}

            Time column: {time_column}
            Event column: {event_column}

            Return Python code in ```python``` format with a single function definition:

            def {function_name}(data_raw):
                import pandas as pd
                import numpy as np
                from lifelines import KaplanMeierFitter, CoxPHFitter
                from lifelines.statistics import logrank_test
                import plotly.graph_objects as go
                ...
                return result_dict

            The function must return a dictionary with these keys:
            - 'survival_results': pd.DataFrame with survival curve data
            - 'plotly_graph': dict (Plotly figure as dict for visualization)
            - 'summary_statistics': dict with key metrics (median survival, etc.)
            - 'model_results': dict with model outputs (Cox coefficients, etc.) if applicable

            Best Practices:
            {best_practices}

            CRITICAL REQUIREMENTS:
            - All imports must be INSIDE the function definition
            - Convert DataFrame to dict before returning (use .to_dict())
            - Convert Plotly figures to dict (use fig.to_dict())
            - Handle missing values appropriately
            - Include error handling for edge cases
            - Validate that time and event columns exist
            - Ensure all returned objects are JSON-serializable
            """,
            input_variables=[
                "recommended_steps",
                "data_summary",
                "time_column",
                "event_column",
                "function_name",
                "best_practices",
            ],
        )

        survival_analysis_agent = survival_analysis_prompt | llm | PythonOutputParser()

        response = survival_analysis_agent.invoke(
            {
                "recommended_steps": steps_for_prompt,
                "data_summary": data_summary_str,
                "time_column": time_column,
                "event_column": event_column,
                "function_name": function_name,
                "best_practices": best_practices,
            }
        )

        response = relocate_imports_inside_function(response)
        response = add_comments_to_top(response, agent_name=AGENT_NAME)

        file_path, file_name_2 = log_ai_function(
            response=response,
            file_name=file_name,
            log=log,
            log_path=log_path,
            overwrite=overwrite,
        )

        return {
            "survival_analyzer_function": response,
            "survival_analyzer_function_path": file_path,
            "survival_analyzer_file_name": file_name_2,
            "survival_analyzer_function_name": function_name,
            "data_summary": data_summary_str,
            "recommended_steps": steps_for_prompt,
        }

    # Human Review
    prompt_text_human_review = "Are the following survival analysis instructions correct? (Answer 'yes' or provide modifications)\n{steps}"

    if not bypass_explain_code:

        def human_review(state: GraphState):
            return node_func_human_review(
                state=state,
                prompt_text=prompt_text_human_review,
                yes_goto="report_agent_outputs",
                no_goto="recommend_analysis_steps",
                user_instructions_key="user_instructions",
                recommended_steps_key="recommended_steps",
                code_snippet_key="survival_analyzer_function",
            )
    else:

        def human_review(state: GraphState):
            return node_func_human_review(
                state=state,
                prompt_text=prompt_text_human_review,
                yes_goto="__end__",
                no_goto="recommend_analysis_steps",
                user_instructions_key="user_instructions",
                recommended_steps_key="recommended_steps",
                code_snippet_key="survival_analyzer_function",
            )

    def execute_survival_analyzer_code(state: GraphState):
        print("    * EXECUTE SURVIVAL ANALYZER CODE (SANDBOXED)")

        result, error = run_code_sandboxed_subprocess(
            code_snippet=state.get("survival_analyzer_function"),
            function_name=state.get("survival_analyzer_function_name"),
            data=state.get("data_raw"),
            timeout=30,  # Longer timeout for survival analysis
            memory_limit_mb=512,
        )

        survival_results = None
        plotly_graph = None
        validation_error = None

        if error is None:
            try:
                if isinstance(result, dict):
                    survival_results = result.get("survival_results")
                    plotly_graph = result.get("plotly_graph")

                    if survival_results is None:
                        validation_error = "Function did not return 'survival_results' key"
                else:
                    validation_error = f"Function must return a dictionary, got {type(result)}"
            except Exception as exc:
                validation_error = f"Error processing survival analysis results: {exc}"
        else:
            validation_error = error

        error_prefixed = (
            f"An error occurred during survival analysis: {validation_error}"
            if validation_error
            else None
        )

        error_log_path = None
        if error_prefixed and log:
            error_log_path = log_ai_error(
                error_message=error_prefixed,
                file_name=f"{file_name}_errors.log",
                log=log,
                log_path=log_path if log_path is not None else LOG_PATH,
                overwrite=False,
            )
            if error_log_path:
                print(f"      Error logged to: {error_log_path}")

        return {
            "survival_results": survival_results,
            "plotly_graph": plotly_graph,
            "survival_analyzer_error": error_prefixed,
            "survival_analyzer_error_log_path": error_log_path,
        }

    def fix_survival_analyzer_code(state: GraphState):
        survival_analyzer_prompt = """
        You are a Survival Analysis Agent. Your {function_name}() function is currently broken and needs fixing.

        Return Python code in ```python``` format with a single function definition, {function_name}(data_raw),
        that includes all imports inside the function.

        This is the broken code (please fix):
        {code_snippet}

        Last Known Error:
        {error}

        User Instructions:
        {user_instructions}

        Recommended Steps:
        {recommended_steps}
        """

        return node_func_fix_agent_code(
            state=state,
            code_snippet_key="survival_analyzer_function",
            error_key="survival_analyzer_error",
            llm=llm,
            prompt_template=survival_analyzer_prompt,
            agent_name=AGENT_NAME,
            log=log,
            file_path=state.get("survival_analyzer_function_path"),
            function_name=state.get("survival_analyzer_function_name"),
        )

    def report_agent_outputs(state: GraphState):
        return node_func_report_agent_outputs(
            state=state,
            keys_to_include=[
                "recommended_steps",
                "survival_analyzer_function",
                "survival_analyzer_function_path",
                "survival_analyzer_function_name",
                "survival_analyzer_error",
                "survival_analyzer_error_log_path",
            ],
            result_key="messages",
            role=AGENT_NAME,
            custom_title="Survival Analysis Agent Outputs",
        )

    node_functions = {
        "recommend_analysis_steps": recommend_analysis_steps,
        "human_review": human_review,
        "create_survival_analyzer_code": create_survival_analyzer_code,
        "execute_survival_analyzer_code": execute_survival_analyzer_code,
        "fix_survival_analyzer_code": fix_survival_analyzer_code,
        "report_agent_outputs": report_agent_outputs,
    }

    app = create_coding_agent_graph(
        GraphState=GraphState,
        node_functions=node_functions,
        recommended_steps_node_name="recommend_analysis_steps",
        create_code_node_name="create_survival_analyzer_code",
        execute_code_node_name="execute_survival_analyzer_code",
        fix_code_node_name="fix_survival_analyzer_code",
        explain_code_node_name="report_agent_outputs",
        error_key="survival_analyzer_error",
        human_in_the_loop=human_in_the_loop,
        human_review_node_name="human_review",
        checkpointer=checkpointer,
        bypass_recommended_steps=bypass_recommended_steps,
        bypass_explain_code=bypass_explain_code,
        agent_name=AGENT_NAME,
    )

    return app
