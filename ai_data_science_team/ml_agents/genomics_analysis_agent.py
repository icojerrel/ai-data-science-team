# BUSINESS SCIENCE UNIVERSITY
# AI DATA SCIENCE TEAM
# ***
# * ML Agents: Genomics Analysis Agent

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
from ai_data_science_team.tools.genomics import (
    get_genomics_data_summary,
    validate_genomics_data,
    get_genomics_analysis_best_practices,
    get_common_cancer_genes,
    get_cancer_pathways,
)
from ai_data_science_team.utils.logging import log_ai_function, log_ai_error
from ai_data_science_team.utils.sandbox import run_code_sandboxed_subprocess
from ai_data_science_team.utils.messages import get_last_user_message_content

# Setup
AGENT_NAME = "genomics_analysis_agent"
LOG_PATH = os.path.join(os.getcwd(), "logs/")


class GenomicsAnalysisAgent(BaseAgent):
    """
    Creates a genomics analysis agent for analyzing mutation data, identifying driver
    genes, and performing pathway enrichment in cancer research.

    This agent is specifically designed for cancer genomics research where mutation
    analysis is critical for:
    - Driver gene identification
    - Pathway enrichment analysis
    - Tumor mutational burden (TMB) calculation
    - Mutation signature analysis
    - Actionable mutation discovery
    - Multi-omics integration

    Parameters
    ----------
    model : langchain.llms.base.LLM
        The language model used to generate the genomics analysis function.
    gene_column : str, optional
        Name of the column containing gene names. Defaults to "gene".
    mutation_column : str, optional
        Name of the column containing mutation types. Defaults to "mutation_type".
    n_samples : int, optional
        Number of samples used when summarizing the dataset. Defaults to 30.
    log : bool, optional
        Whether to log the generated code and errors. Defaults to False.
    log_path : str, optional
        Directory path for storing log files. Defaults to None.
    file_name : str, optional
        Name of the file for saving the generated response. Defaults to "genomics_analyzer.py".
    function_name : str, optional
        Name of the generated genomics analysis function. Defaults to "genomics_analyzer".
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
        Performs genomics analysis on the provided dataset based on user instructions.
    get_genomics_results()
        Retrieves the genomics analysis results as a pandas DataFrame.
    get_plotly_graph()
        Retrieves the generated visualization as a Plotly graph object.
    get_genomics_analyzer_function()
        Retrieves the generated Python function used for genomics analysis.

    Examples
    --------
    ```python
    import pandas as pd
    from langchain_openai import ChatOpenAI
    from ai_data_science_team.ml_agents import GenomicsAnalysisAgent

    llm = ChatOpenAI(model="gpt-4o-mini")

    # Create genomics analysis agent
    genomics_agent = GenomicsAnalysisAgent(
        model=llm,
        gene_column="gene",
        mutation_column="mutation_type",
        log=True
    )

    # Load mutation data
    df = pd.read_csv("somatic_mutations.csv")

    # Identify driver genes
    genomics_agent.invoke_agent(
        user_instructions="Identify driver genes and perform pathway enrichment analysis",
        data_raw=df
    )

    # Get results
    results = genomics_agent.get_genomics_results()
    plot = genomics_agent.get_plotly_graph()
    ```

    Returns
    --------
    GenomicsAnalysisAgent : langchain.graphs.CompiledStateGraph
        A genomics analysis agent implemented as a compiled state graph.
    """

    def __init__(
        self,
        model,
        gene_column: str = "gene",
        mutation_column: str = "mutation_type",
        n_samples=30,
        log=False,
        log_path=None,
        file_name="genomics_analyzer.py",
        function_name="genomics_analyzer",
        overwrite=True,
        human_in_the_loop=False,
        bypass_recommended_steps=False,
        bypass_explain_code=False,
        checkpointer: Checkpointer = None,
    ):
        self._params = {
            "model": model,
            "gene_column": gene_column,
            "mutation_column": mutation_column,
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
        """Invokes the agent."""
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
        """Asynchronously invokes the agent."""
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
        """Invokes the agent with explicit message list."""
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
        """Create the compiled graph for the genomics analysis agent."""
        self.response = None
        return make_genomics_analysis_agent(**self._params)

    def get_genomics_results(self):
        """Retrieves the genomics analysis results."""
        if self.response:
            return pd.DataFrame(self.response.get("genomics_results"))

    def get_plotly_graph(self):
        """Retrieves the Plotly graph if one was generated."""
        if self.response and self.response.get("plotly_graph"):
            try:
                import plotly.graph_objects as go

                return go.Figure(self.response.get("plotly_graph"))
            except ImportError:
                print("Plotly not installed. Install with: pip install plotly")
                return None

    def get_genomics_analyzer_function(self, markdown=False):
        """Retrieves the agent's genomics analysis function."""
        if self.response:
            if markdown:
                return Markdown(
                    f"```python\n{self.response.get('genomics_analyzer_function')}\n```"
                )
            else:
                return self.response.get("genomics_analyzer_function")

    def get_recommended_analysis_steps(self, markdown=False):
        """Retrieves the agent's recommended analysis steps."""
        if self.response:
            if markdown:
                return Markdown(self.response.get("recommended_steps"))
            else:
                return self.response.get("recommended_steps")


def make_genomics_analysis_agent(
    model,
    gene_column: str = "gene",
    mutation_column: str = "mutation_type",
    n_samples=30,
    log=False,
    log_path=None,
    file_name="genomics_analyzer.py",
    function_name="genomics_analyzer",
    overwrite=True,
    human_in_the_loop=False,
    bypass_recommended_steps=False,
    bypass_explain_code=False,
    checkpointer: Checkpointer = None,
):
    """
    Creates a genomics analysis agent for mutation and pathway analysis.

    The agent performs genomics analysis including:
    - Driver gene identification
    - Mutation type distribution
    - Pathway enrichment analysis
    - Tumor mutational burden (TMB)
    - Actionable mutation discovery
    - Mutation visualization (oncoprints, lollipop plots)

    Parameters
    ----------
    model : langchain.llms.base.LLM
        The language model to use to generate code.
    gene_column : str
        Name of the column containing gene names.
    mutation_column : str
        Name of the column containing mutation types.
    n_samples : int, optional
        The number of samples to use when summarizing the dataset.
    log : bool, optional
        Whether or not to log the code generated.
    log_path : str, optional
        The path to the directory where the log files should be stored.
    file_name : str, optional
        The name of the file to save the response to.
    function_name : str, optional
        The name of the function that will be generated.
    overwrite : bool, optional
        Whether or not to overwrite the log file if it already exists.
    human_in_the_loop : bool, optional
        Whether or not to use human in the loop.
    bypass_recommended_steps : bool, optional
        Bypass the recommendation step.
    bypass_explain_code : bool, optional
        Bypass the code explanation step.
    checkpointer : langgraph.types.Checkpointer, optional
        Checkpointer to save and load the agent's state.

    Returns
    -------
    app : langchain.graphs.CompiledStateGraph
        The genomics analysis agent as a state graph.
    """
    llm = model

    # Get cancer gene and pathway references
    cancer_genes = get_common_cancer_genes()
    cancer_pathways = get_cancer_pathways()

    DEFAULT_ANALYSIS_STEPS = format_recommended_steps(
        """
1. Validate genomics data (gene names, mutation types, positions).
2. Identify frequently mutated genes and compare to known cancer drivers.
3. Categorize mutations by type (missense, nonsense, frameshift, etc.).
4. Calculate tumor mutational burden (TMB) if applicable.
5. Perform pathway enrichment analysis using known cancer pathways.
6. Flag actionable/targetable mutations.
7. Create visualizations (mutation frequency plot, pathway heatmap, oncoprint).
8. Return summary statistics including top mutated genes and enriched pathways.
        """,
        heading="# Recommended Genomics Analysis Steps:",
    )

    best_practices = get_genomics_analysis_best_practices()

    def _summarize_genomics_data(df: pd.DataFrame) -> str:
        """Summarize genomics data for prompts."""
        return get_genomics_data_summary(
            df, gene_column, mutation_column, n_sample=min(n_samples, 10)
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
        genomics_results: dict
        plotly_graph: dict
        data_summary: str
        genomics_analyzer_function: str
        genomics_analyzer_function_path: str
        genomics_analyzer_file_name: str
        genomics_analyzer_function_name: str
        genomics_analyzer_error: str
        genomics_analyzer_error_log_path: str
        max_retries: int
        retry_count: int

    def recommend_analysis_steps(state: GraphState):
        """Recommend genomics analysis steps based on the data."""
        print(format_agent_name(AGENT_NAME))
        print("    * RECOMMEND GENOMICS ANALYSIS STEPS")

        recommend_steps_prompt = PromptTemplate(
            template="""
            You are a Cancer Genomics Expert specializing in mutation analysis and
            precision oncology. Given the following genomics data, recommend a series
            of numbered analysis steps.

            General Genomics Analysis Steps:

            * Validate data (gene names, mutation types, positions)
            * Identify driver genes vs passenger mutations
            * Calculate mutation frequencies and recurrence
            * Categorize mutations by functional impact
            * Perform pathway enrichment analysis
            * Calculate tumor mutational burden (TMB)
            * Identify actionable/targetable mutations
            * Visualize mutation patterns

            Custom Steps:
            * Analyze the data structure to determine appropriate analyses
            * Consider presence of clinical annotations (VAF, coverage, etc.)
            * Identify potential mutation signatures
            * Recommend visualization strategies

            Known Cancer Driver Genes (for reference):
            {cancer_genes}

            Cancer Pathways Available for Analysis:
            {cancer_pathways}

            IMPORTANT:
            Take into account user instructions that may specify particular analyses.
            Include comments explaining your reasoning for each step.

            User instructions:
            {user_instructions}

            Previously Recommended Steps (if any):
            {recommended_steps}

            Genomics Data Summary:
            {data_summary}

            Return steps as a numbered list. You can include short code snippets for clarity,
            but do not provide a complete implementation.

            Best Practices to Consider:
            {best_practices}
            """,
            input_variables=[
                "user_instructions",
                "recommended_steps",
                "data_summary",
                "best_practices",
                "cancer_genes",
                "cancer_pathways",
            ],
        )

        data_raw = state.get("data_raw")
        df = pd.DataFrame.from_dict(data_raw)

        # Validate genomics data
        is_valid, issues = validate_genomics_data(df, required_columns=None)
        if not is_valid:
            warning_msg = "Genomics data validation warnings:\n" + "\n".join(issues)
            print(f"      WARNING: {warning_msg}")

        data_summary_str = _summarize_genomics_data(df)

        # Format references for prompt
        cancer_genes_str = ", ".join(cancer_genes[:20]) + " (and more...)"
        pathways_str = ", ".join(list(cancer_pathways.keys()))

        steps_agent = recommend_steps_prompt | llm
        recommended_steps = steps_agent.invoke(
            {
                "user_instructions": state.get("user_instructions"),
                "recommended_steps": state.get("recommended_steps"),
                "data_summary": data_summary_str,
                "best_practices": best_practices,
                "cancer_genes": cancer_genes_str,
                "cancer_pathways": pathways_str,
            }
        )

        return {
            "recommended_steps": format_recommended_steps(
                recommended_steps.content.strip(),
                heading="# Recommended Genomics Analysis Steps:",
            ),
            "data_summary": data_summary_str,
        }

    def create_genomics_analyzer_code(state: GraphState):
        print("    * CREATE GENOMICS ANALYZER CODE")

        if bypass_recommended_steps:
            print(format_agent_name(AGENT_NAME))
            data_raw = state.get("data_raw")
            df = pd.DataFrame.from_dict(data_raw)
            data_summary_str = _summarize_genomics_data(df)
            steps_for_prompt = DEFAULT_ANALYSIS_STEPS
        else:
            data_summary_str = state.get("data_summary")
            steps_for_prompt = state.get("recommended_steps") or DEFAULT_ANALYSIS_STEPS

        # Format references
        cancer_genes_str = str(cancer_genes)
        pathways_str = str(cancer_pathways)

        genomics_analysis_prompt = PromptTemplate(
            template="""
            You are a Genomics Analysis Agent. Create a {function_name}() function that performs
            genomics/mutation analysis on the provided data following these recommended steps.

            Recommended Steps:
            {recommended_steps}

            You can use these libraries:
            - pandas, numpy: For data manipulation
            - plotly.graph_objects: For interactive visualizations
            - collections.Counter: For counting frequencies

            Genomics Data Summary:
            {data_summary}

            Gene column: {gene_column}
            Mutation type column: {mutation_column}

            Known Cancer Driver Genes (use for comparison):
            {cancer_genes}

            Cancer Pathways (use for enrichment):
            {cancer_pathways}

            Return Python code in ```python``` format with a single function definition:

            def {function_name}(data_raw):
                import pandas as pd
                import numpy as np
                import plotly.graph_objects as go
                from collections import Counter
                ...
                return result_dict

            The function must return a dictionary with these keys:
            - 'genomics_results': pd.DataFrame with analysis results
            - 'plotly_graph': dict (Plotly figure as dict for visualization)
            - 'summary_statistics': dict with key metrics (top genes, TMB, etc.)
            - 'pathway_enrichment': dict with enriched pathways if applicable
            - 'driver_genes': list of identified driver genes

            Best Practices:
            {best_practices}

            CRITICAL REQUIREMENTS:
            - All imports must be INSIDE the function definition
            - Convert DataFrame to dict before returning (use .to_dict())
            - Convert Plotly figures to dict (use fig.to_dict())
            - Handle missing values appropriately
            - Validate that gene and mutation columns exist
            - Ensure all returned objects are JSON-serializable
            - Include meaningful error messages for edge cases
            """,
            input_variables=[
                "recommended_steps",
                "data_summary",
                "gene_column",
                "mutation_column",
                "function_name",
                "best_practices",
                "cancer_genes",
                "cancer_pathways",
            ],
        )

        genomics_analysis_agent = genomics_analysis_prompt | llm | PythonOutputParser()

        response = genomics_analysis_agent.invoke(
            {
                "recommended_steps": steps_for_prompt,
                "data_summary": data_summary_str,
                "gene_column": gene_column,
                "mutation_column": mutation_column,
                "function_name": function_name,
                "best_practices": best_practices,
                "cancer_genes": cancer_genes_str,
                "cancer_pathways": pathways_str,
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
            "genomics_analyzer_function": response,
            "genomics_analyzer_function_path": file_path,
            "genomics_analyzer_file_name": file_name_2,
            "genomics_analyzer_function_name": function_name,
            "data_summary": data_summary_str,
            "recommended_steps": steps_for_prompt,
        }

    # Human Review
    prompt_text_human_review = "Are the following genomics analysis instructions correct? (Answer 'yes' or provide modifications)\n{steps}"

    if not bypass_explain_code:

        def human_review(state: GraphState):
            return node_func_human_review(
                state=state,
                prompt_text=prompt_text_human_review,
                yes_goto="report_agent_outputs",
                no_goto="recommend_analysis_steps",
                user_instructions_key="user_instructions",
                recommended_steps_key="recommended_steps",
                code_snippet_key="genomics_analyzer_function",
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
                code_snippet_key="genomics_analyzer_function",
            )

    def execute_genomics_analyzer_code(state: GraphState):
        print("    * EXECUTE GENOMICS ANALYZER CODE (SANDBOXED)")

        result, error = run_code_sandboxed_subprocess(
            code_snippet=state.get("genomics_analyzer_function"),
            function_name=state.get("genomics_analyzer_function_name"),
            data=state.get("data_raw"),
            timeout=30,  # Longer timeout for genomics analysis
            memory_limit_mb=512,
        )

        genomics_results = None
        plotly_graph = None
        validation_error = None

        if error is None:
            try:
                if isinstance(result, dict):
                    genomics_results = result.get("genomics_results")
                    plotly_graph = result.get("plotly_graph")

                    if genomics_results is None:
                        validation_error = (
                            "Function did not return 'genomics_results' key"
                        )
                else:
                    validation_error = (
                        f"Function must return a dictionary, got {type(result)}"
                    )
            except Exception as exc:
                validation_error = f"Error processing genomics analysis results: {exc}"
        else:
            validation_error = error

        error_prefixed = (
            f"An error occurred during genomics analysis: {validation_error}"
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
            "genomics_results": genomics_results,
            "plotly_graph": plotly_graph,
            "genomics_analyzer_error": error_prefixed,
            "genomics_analyzer_error_log_path": error_log_path,
        }

    def fix_genomics_analyzer_code(state: GraphState):
        genomics_analyzer_prompt = """
        You are a Genomics Analysis Agent. Your {function_name}() function is currently broken and needs fixing.

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
            code_snippet_key="genomics_analyzer_function",
            error_key="genomics_analyzer_error",
            llm=llm,
            prompt_template=genomics_analyzer_prompt,
            agent_name=AGENT_NAME,
            log=log,
            file_path=state.get("genomics_analyzer_function_path"),
            function_name=state.get("genomics_analyzer_function_name"),
        )

    def report_agent_outputs(state: GraphState):
        return node_func_report_agent_outputs(
            state=state,
            keys_to_include=[
                "recommended_steps",
                "genomics_analyzer_function",
                "genomics_analyzer_function_path",
                "genomics_analyzer_function_name",
                "genomics_analyzer_error",
                "genomics_analyzer_error_log_path",
            ],
            result_key="messages",
            role=AGENT_NAME,
            custom_title="Genomics Analysis Agent Outputs",
        )

    node_functions = {
        "recommend_analysis_steps": recommend_analysis_steps,
        "human_review": human_review,
        "create_genomics_analyzer_code": create_genomics_analyzer_code,
        "execute_genomics_analyzer_code": execute_genomics_analyzer_code,
        "fix_genomics_analyzer_code": fix_genomics_analyzer_code,
        "report_agent_outputs": report_agent_outputs,
    }

    app = create_coding_agent_graph(
        GraphState=GraphState,
        node_functions=node_functions,
        recommended_steps_node_name="recommend_analysis_steps",
        create_code_node_name="create_genomics_analyzer_code",
        execute_code_node_name="execute_genomics_analyzer_code",
        fix_code_node_name="fix_genomics_analyzer_code",
        explain_code_node_name="report_agent_outputs",
        error_key="genomics_analyzer_error",
        human_in_the_loop=human_in_the_loop,
        human_review_node_name="human_review",
        checkpointer=checkpointer,
        bypass_recommended_steps=bypass_recommended_steps,
        bypass_explain_code=bypass_explain_code,
        agent_name=AGENT_NAME,
    )

    return app
