# CLAUDE.md - AI Assistant Guide for AI Data Science Team

## Project Overview

**AI Data Science Team** is an AI-powered framework that provides a team of specialized agents to perform common data science tasks. The project uses LangGraph and LangChain to orchestrate multiple AI agents that collaborate on data science workflows.

### Key Technologies
- **LangChain/LangGraph**: Agent orchestration and state management
- **Python 3.9+**: Primary language
- **Pandas**: Data manipulation
- **H2O AutoML**: Automated machine learning
- **MLflow**: ML experiment tracking and model management
- **Streamlit**: Web application framework
- **Plotly**: Interactive visualizations
- **SQLAlchemy**: Database connectivity

### Project Purpose
Enable users to perform complex data science tasks 10X faster by leveraging specialized AI agents for data cleaning, wrangling, visualization, feature engineering, modeling, and analysis.

---

## Repository Structure

```
ai-data-science-team/
├── ai_data_science_team/          # Main package
│   ├── agents/                     # Individual specialized agents
│   │   ├── data_cleaning_agent.py
│   │   ├── data_wrangling_agent.py
│   │   ├── data_visualization_agent.py
│   │   ├── feature_engineering_agent.py
│   │   ├── data_loader_tools_agent.py
│   │   └── sql_database_agent.py
│   ├── ml_agents/                  # Machine learning agents
│   │   ├── h2o_ml_agent.py        # H2O AutoML integration
│   │   ├── mlflow_tools_agent.py  # MLflow operations
│   │   └── model_evaluation_agent.py
│   ├── ds_agents/                  # Data science agents
│   │   └── eda_tools_agent.py     # Exploratory Data Analysis
│   ├── multiagents/                # Multi-agent systems
│   │   ├── pandas_data_analyst.py # Combines wrangling + visualization
│   │   ├── sql_data_analyst.py    # SQL + visualization
│   │   └── supervisor_ds_team.py  # Orchestrates multiple agents
│   ├── tools/                      # Shared tools and utilities
│   │   ├── dataframe.py           # DataFrame utilities
│   │   ├── data_loader.py         # Data loading tools
│   │   ├── eda.py                 # EDA tools
│   │   ├── h2o.py                 # H2O AutoML tools
│   │   ├── mlflow.py              # MLflow tools
│   │   └── sql.py                 # SQL tools
│   ├── templates/                  # Agent templates and base classes
│   │   └── agent_templates.py     # BaseAgent, helper functions
│   ├── parsers/                    # Output parsers
│   │   └── parsers.py             # PythonOutputParser
│   ├── utils/                      # Utility modules
│   │   ├── logging.py             # Logging utilities
│   │   ├── messages.py            # Message handling
│   │   ├── regex.py               # Code manipulation utilities
│   │   ├── sandbox.py             # Sandboxed code execution
│   │   ├── plotly.py              # Plotly utilities
│   │   ├── matplotlib.py          # Matplotlib utilities
│   │   └── pipeline.py            # Pipeline utilities
│   └── orchestration.py           # Orchestration logic (TODO)
├── apps/                           # Streamlit applications
│   ├── exploratory-copilot-app/   # EDA copilot
│   ├── pandas-data-analyst-app/   # Pandas analyst
│   ├── sql-database-agent-app/    # SQL database agent
│   └── supervisor-ds-team-app/    # Supervisor team
├── examples/                       # Jupyter notebook examples
│   ├── multiagents/               # Multi-agent examples
│   ├── ml_agents/                 # ML agent examples
│   ├── ds_agents/                 # DS agent examples
│   └── advanced_topics/           # Advanced examples
├── data/                           # Sample datasets
├── planning_docs/                  # Planning documentation
├── requirements.txt                # Dependencies
├── setup.py                        # Package setup
└── README.md                       # Project README
```

---

## Architecture & Design Patterns

### Agent Architecture

All agents follow a consistent pattern based on LangGraph's StateGraph:

1. **BaseAgent Class** (`templates/agent_templates.py:26`):
   - Wraps `CompiledStateGraph` from LangGraph
   - Provides common interface: `invoke()`, `ainvoke()`, `stream()`, etc.
   - Manages state, checkpointing, and configuration
   - All agents inherit from this base class

2. **Agent Pattern**:
   ```python
   class DataCleaningAgent(BaseAgent):
       def __init__(self, model, **params):
           self._params = {...}
           self._compiled_graph = self._make_compiled_graph()
           self.response = None

       def invoke_agent(self, data_raw, user_instructions, **kwargs):
           # Simplified interface for users

       def _make_compiled_graph(self):
           # Build LangGraph StateGraph
   ```

3. **State Management**:
   - Each agent defines a `GraphState` (TypedDict) with specific keys
   - State flows through nodes in the graph
   - Messages are accumulated using `Annotated[Sequence[BaseMessage], operator.add]`

### Coding Agent Pattern

Most agents follow a "coding agent" workflow (`templates/agent_templates.py:278`):

```
START → recommend_steps → [human_review] → create_code → execute_code → [fix_code] → report_outputs → END
                                                              ↓
                                                         error? → fix_code → execute_code
```

**Key Nodes**:
- **recommend_steps**: LLM generates recommended data processing steps
- **human_review**: Optional interrupt for human approval
- **create_code**: LLM generates Python function to perform task
- **execute_code**: Run generated code in sandboxed environment
- **fix_code**: If error occurs and retries available, fix the code
- **report_outputs**: Final reporting of results

### Multi-Agent Systems

Multi-agents coordinate multiple specialized agents (`multiagents/`):

**Example: PandasDataAnalyst** (`multiagents/pandas_data_analyst.py:26`):
- Orchestrates `DataWranglingAgent` + `DataVisualizationAgent`
- Routes user requests to appropriate agents
- Decides whether to return chart or table
- Combines outputs into unified response

---

## Key Conventions & Patterns

### 1. Code Generation & Execution

**Generated Functions**:
- All agents generate Python functions with specific signatures
- Example: `data_cleaner(data_raw)` returns `data_cleaned`
- Imports are relocated inside function definitions for safety
- Code includes comments from the agent name

**Sandboxed Execution** (`utils/sandbox.py`):
- Generated code runs in subprocess with resource limits
- Timeout and memory constraints prevent runaway processes
- Results serialized via pickle for safe transfer

### 2. Logging

**Log Structure** (`utils/logging.py`):
- Generated code saved to `log_path` directory
- Error logs saved separately with `.log` extension
- Functions: `log_ai_function()`, `log_ai_error()`

### 3. Data Flow

**Data Serialization**:
- DataFrames converted to dict: `df.to_dict()`
- State stores dicts, not DataFrames
- Agents reconstruct DataFrames: `pd.DataFrame.from_dict(data_raw)`

**Common State Keys**:
- `data_raw`: Input data (dict)
- `data_cleaned`/`data_wrangled`: Output data (dict)
- `user_instructions`: User's natural language request
- `recommended_steps`: LLM-generated processing steps
- `*_function`: Generated Python code
- `*_function_path`: Path to logged code file
- `*_error`: Error message if execution failed
- `max_retries`: Maximum retry attempts
- `retry_count`: Current retry count

### 4. Message Handling

**Message Roles** (`utils/messages.py`):
- Agents use custom roles (e.g., `"data_cleaning_agent"`)
- Multi-agents filter messages by role
- `remove_consecutive_duplicates()` dedupes messages

### 5. Human-in-the-Loop

**Interrupt Pattern** (`templates/agent_templates.py:444`):
- Uses LangGraph's `interrupt()` function
- Requires checkpointer (e.g., `MemorySaver()`)
- Returns `Command` object for routing
- User can approve ("yes") or provide modifications

---

## Development Workflows

### Creating a New Agent

1. **Define GraphState**:
   ```python
   class GraphState(TypedDict):
       messages: Annotated[Sequence[BaseMessage], operator.add]
       user_instructions: str
       data_raw: dict
       data_processed: dict
       agent_function: str
       agent_error: str
       max_retries: int
       retry_count: int
   ```

2. **Create Node Functions**:
   - `recommend_steps(state)`: Generate recommendations
   - `create_code(state)`: Generate Python function
   - `execute_code(state)`: Run generated code
   - `fix_code(state)`: Fix errors if needed
   - `report_outputs(state)`: Final reporting

3. **Use Template**:
   ```python
   app = create_coding_agent_graph(
       GraphState=GraphState,
       node_functions=node_functions,
       recommended_steps_node_name="recommend_steps",
       create_code_node_name="create_code",
       execute_code_node_name="execute_code",
       fix_code_node_name="fix_code",
       explain_code_node_name="report_outputs",
       error_key="agent_error",
       agent_name="my_agent"
   )
   ```

4. **Wrap in BaseAgent Class**:
   ```python
   class MyAgent(BaseAgent):
       def __init__(self, model, **params):
           self._params = {...}
           self._compiled_graph = self._make_compiled_graph()
           self.response = None

       def _make_compiled_graph(self):
           return make_my_agent(**self._params)

       def invoke_agent(self, data_raw, user_instructions, **kwargs):
           self.response = self.invoke({...})
   ```

### Creating a Multi-Agent

1. **Instantiate Sub-Agents**:
   ```python
   wrangling_agent = DataWranglingAgent(model=llm, ...)
   viz_agent = DataVisualizationAgent(model=llm, ...)
   ```

2. **Create Routing Logic**:
   - Use LLM to parse user request
   - Determine which agents to invoke
   - Handle sequential or conditional routing

3. **Invoke Sub-Agents**:
   ```python
   response = data_wrangling_agent.invoke({
       "user_instructions": processed_instructions,
       "data_raw": state.get("data_raw"),
       ...
   })
   ```

4. **Aggregate Results**:
   - Combine messages from all agents
   - Return unified response

### Running Examples

**Jupyter Notebooks** (`examples/`):
```bash
# Install dependencies
pip install ai-data-science-team

# Run example notebook
jupyter notebook examples/data_cleaning_agent.ipynb
```

**Streamlit Apps** (`apps/`):
```bash
# Navigate to app directory
cd apps/pandas-data-analyst-app

# Run app
streamlit run app.py
```

---

## Critical Implementation Details

### 1. Import Handling

**Pattern** (`utils/regex.py`):
- `relocate_imports_inside_function()`: Moves imports inside function definitions
- Prevents namespace pollution and import conflicts
- Example:
  ```python
  # Before
  import pandas as pd
  def my_func(data):
      ...

  # After
  def my_func(data):
      import pandas as pd
      ...
  ```

### 2. Error Recovery

**Retry Logic**:
- Agents track `retry_count` and `max_retries`
- On error, invoke `fix_code` node
- LLM receives error message and broken code
- Generate fixed code and retry execution
- Max 3 retries by default

### 3. Prompt Engineering

**Key Principles**:
- Provide data summaries, not full datasets
- Limit columns: `MAX_SUMMARY_COLUMNS = 30`
- Include `get_dataframe_summary()` with sample rows
- Specify expected output format clearly
- Include best practices in prompts to prevent common errors

**Example Best Practice** (`agents/data_cleaning_agent.py:641`):
```
Always ensure that when assigning the output of fit_transform() from
SimpleImputer to a Pandas DataFrame column, you call .ravel() or
flatten the array, because fit_transform() returns a 2D array while
a DataFrame column is 1D.
```

### 4. Data Summarization

**DataFrame Summary** (`tools/dataframe.py`):
- `get_dataframe_summary()`: Creates concise data overview
- Includes: shape, dtypes, sample rows, missing values
- Truncated to avoid token limits
- Used in prompts to inform agent decisions

### 5. Visualization Handling

**Plotly Serialization** (`utils/plotly.py`):
- Store graphs as dicts: `fig.to_dict()`
- Reconstruct: `plotly_from_dict(graph_dict)`
- JSON-serializable for state management

---

## Testing & Quality Assurance

### Current Status
- Beta version (pre-0.1.0)
- Breaking changes may occur
- Examples serve as integration tests

### Best Practices for Contributors

1. **Test with Examples**:
   - Run corresponding example notebook after changes
   - Verify agent still produces correct output

2. **Maintain Backward Compatibility**:
   - Avoid breaking changes to agent interfaces
   - Add new parameters as optional

3. **Follow Naming Conventions**:
   - Agent classes: `{Purpose}Agent` (e.g., `DataCleaningAgent`)
   - Factory functions: `make_{purpose}_agent()`
   - State keys: `{agent}_{purpose}` (e.g., `data_cleaner_function`)

4. **Document Changes**:
   - Update docstrings
   - Add example usage
   - Update relevant README files

---

## Common Pitfalls & Solutions

### 1. Token Limit Exceeded

**Problem**: "This model's maximum context length is 128000 tokens..."

**Solutions**:
- Reduce `n_samples` parameter when creating agent
- Limit data summary columns
- Truncate large text outputs

### 2. Sandboxed Execution Timeout

**Problem**: Code execution times out

**Solutions**:
- Increase `timeout` parameter in sandbox
- Optimize generated code (provide hints in prompt)
- Use smaller data samples for testing

### 3. Import Errors in Generated Code

**Problem**: Module not found or import conflicts

**Solutions**:
- Ensure `relocate_imports_inside_function()` is called
- Specify allowed libraries in prompt
- Check sandbox environment has required packages

### 4. State Key Mismatches

**Problem**: Agent can't find expected state keys

**Solutions**:
- Check `GraphState` TypedDict definition
- Ensure all nodes return correct state keys
- Use `state.get(key, default)` for optional keys

### 5. Multi-Agent Message Confusion

**Problem**: Messages from different agents mixed up

**Solutions**:
- Use distinct `role` for each agent's messages
- Call `remove_consecutive_duplicates()` on messages
- Filter messages by role when needed

---

## Environment Setup

### Installation

**Basic Install**:
```bash
pip install ai-data-science-team
```

**From Source**:
```bash
git clone https://github.com/business-science/ai-data-science-team.git
cd ai-data-science-team
pip install -e .
```

**With Optional Dependencies**:
```bash
# Machine Learning
pip install ai-data-science-team[machine_learning]

# Data Science
pip install ai-data-science-team[data_science]

# All extras
pip install ai-data-science-team[all]
```

### Required Environment Variables

```bash
# OpenAI (or other LLM provider)
export OPENAI_API_KEY="your-api-key"

# Optional: OpenRouter (10-100x cheaper than direct API)
export OPENROUTER_API_KEY="sk-or-v1-..."  # Get from https://openrouter.ai/

# Optional: MLflow tracking
export MLFLOW_TRACKING_URI="sqlite:///mlflow.db"
```

### Python Version
- Minimum: Python 3.9
- Tested: 3.9, 3.10, 3.11, 3.12, 3.13

---

## File Locations & Paths

### Generated Files

**Default Directories**:
- Logs: `logs/` (created automatically)
- H2O Models: `h2o_models/` (gitignored)
- MLflow Runs: `mlruns/` (gitignored)
- Reports: `reports/` (gitignored)

**Configurable Paths**:
```python
agent = DataCleaningAgent(
    model=llm,
    log=True,
    log_path="custom_logs/",    # Custom log directory
    file_name="cleaner.py",     # Custom filename
    overwrite=True              # Overwrite existing files
)
```

### Sample Data
- Location: `data/`
- Example: `data/churn_data.csv`

---

## Working with Git

### Branch Strategy
- Main branch: `main` (or `master`)
- Feature branches: Create from main
- This session: Work on `claude/add-claude-documentation-X4CBi`

### Commit Guidelines

**Good Commit Messages**:
- "Add CLAUDE.md documentation for AI assistants"
- "Fix data cleaning agent error handling"
- "Update pandas data analyst routing logic"

**Not Recommended**:
- "Update files"
- "Fix bug"
- "WIP"

### Pre-Commit Checks
- Ensure code runs without errors
- Test with relevant examples
- Check for unintended file changes

---

## API Patterns

### Agent Invocation

**Synchronous**:
```python
agent.invoke_agent(
    user_instructions="Clean the data",
    data_raw=df,
    max_retries=3,
    retry_count=0
)

# Access results
cleaned_data = agent.get_data_cleaned()
function_code = agent.get_data_cleaner_function()
```

**Asynchronous**:
```python
await agent.ainvoke_agent(
    user_instructions="Clean the data",
    data_raw=df
)
```

**For Multi-Agent Coordination**:
```python
# Use invoke_messages for supervisor/team patterns
agent.invoke_messages(
    messages=messages_from_supervisor,
    data_raw=df
)
```

### Streaming

```python
for chunk in agent.stream(
    input={...},
    stream_mode="values"  # or "updates", "debug"
):
    print(chunk)
```

### State Access

```python
# Get current state
state = agent.get_state(config)

# Get state history
history = agent.get_state_history(config)

# Update state
agent.update_state(config, {"key": "value"})
```

---

## Debugging Tips

### Enable Logging

```python
agent = DataCleaningAgent(
    model=llm,
    log=True,
    log_path="logs/"
)
```

### Inspect Generated Code

```python
# After invoke_agent()
code = agent.get_data_cleaner_function(markdown=True)
print(code)
```

### Check Error Messages

```python
if agent.response.get("data_cleaner_error"):
    print(agent.response["data_cleaner_error"])
```

### Visualize Agent Graph

```python
agent.show(xray=0)  # Show graph structure
```

### Human-in-the-Loop Debugging

```python
agent = DataCleaningAgent(
    model=llm,
    human_in_the_loop=True,
    checkpointer=MemorySaver()
)

# Agent will interrupt for approval
# Allows inspection before execution
```

---

## Performance Considerations

### LLM Model Selection

**Recommended**:
- Development/Testing: `gpt-4o-mini` (faster, cheaper)
- Production: `gpt-4o`, `gpt-4-turbo` (better quality)
- Claude: `claude-3-5-sonnet-20241022` (high quality)

### Cost-Effective Alternative: OpenRouter

**Save 10-100x on API costs** by using OpenRouter instead of direct API access!

OpenRouter (`utils/openrouter.py`) provides a unified gateway to multiple LLM providers at significantly reduced costs:

**Recommended Models for Cancer Research**:
- **Claude 3.5 Sonnet**: ~$3/M tokens (best quality/cost ratio)
- **Claude 3 Haiku**: ~$0.25/M tokens (fast, cheap, high quality)
- **Gemini Pro 1.5**: ~$1.25/M tokens (good balance)
- **Llama 3.1 70B**: ~$0.35/M tokens (budget option)
- **DeepSeek Chat**: ~$0.14/M tokens (ultra-budget, 100-500x cheaper than OpenAI)
- **Qwen 2.5 72B**: ~$0.35/M tokens (ultra-budget, multilingual, Alibaba)
- **Yi Large**: ~$0.30/M tokens (ultra-budget, strong reasoning)
- **Kimi K2**: ~$0.20/M tokens (ultra-budget, excellent long-context, Moonshot AI)

**Setup**:
```python
from ai_data_science_team.utils.openrouter import get_openrouter_llm
import os

# Set API key (get from https://openrouter.ai/)
os.environ['OPENROUTER_API_KEY'] = "sk-or-v1-..."

# Create LLM (drop-in replacement for ChatOpenAI)
llm = get_openrouter_llm(
    model="anthropic/claude-3.5-sonnet",
    temperature=0
)

# Use with any agent
survival_agent = SurvivalAnalysisAgent(
    model=llm,  # Works exactly the same!
    time_column="survival_months",
    event_column="death_event"
)
```

**Cost Comparison** (example: 1M tokens):
- Direct OpenAI GPT-4o: ~$5.00
- OpenRouter Claude 3.5 Sonnet: ~$9.00 (via OpenRouter pricing)
- OpenRouter Claude 3 Haiku: ~$0.75
- OpenRouter Llama 3.1 70B: ~$0.35
- **OpenRouter DeepSeek Chat: ~$0.21 (🔥 96% cheaper than OpenAI)**
- **OpenRouter Qwen 2.5 72B: ~$0.42 (🔥 92% cheaper than OpenAI)**

**Utility Functions** (`utils/openrouter.py`):
- `get_openrouter_llm(model, temperature, **kwargs)`: Create LangChain-compatible LLM
- `get_cost_estimate(model, input_tokens, output_tokens)`: Estimate costs
- `list_recommended_models()`: View categorized model recommendations
- `compare_costs(openai_model, openrouter_model, tokens)`: Compare pricing

**Benefits**:
- 10-100x cheaper than direct API access
- Access to Claude, Llama, Mistral, Gemini, and more
- LangChain-compatible (no code changes needed)
- Pay only for what you use
- Perfect for high-volume cancer research workflows

**See Examples**:
- `examples/ml_agents/survival_analysis_agent.ipynb` (cells 4-7)
- `examples/ml_agents/genomics_analysis_agent.ipynb` (cells 4-6)

### Optimization Strategies

1. **Reduce Token Usage**:
   - Decrease `n_samples` parameter
   - Limit data summary columns
   - Use `bypass_recommended_steps=True` for simple tasks

2. **Parallel Execution**:
   - Use `ainvoke_agent()` for async operations
   - Run independent agents concurrently

3. **Caching**:
   - Reuse agent instances
   - Cache common transformations
   - Store intermediate results

---

## Security Considerations

### Sandboxed Execution

**Built-in Protections**:
- Subprocess isolation
- Memory limits (default 512MB)
- Timeout limits (default 10s)
- No filesystem access outside working directory

### User Input Validation

**Important**:
- Agents execute LLM-generated code
- Suitable for trusted environments
- Not recommended for untrusted user inputs without review

### API Key Management

**Best Practices**:
- Use environment variables
- Never commit API keys
- Rotate keys regularly
- Use minimum required permissions

---

## Additional Resources

### Documentation
- Main README: `/README.md`
- Apps README: `/apps/README.md`
- Examples README: `/examples/README.md`

### Examples
- Individual agents: `/examples/*.ipynb`
- Multi-agents: `/examples/multiagents/*.ipynb`
- ML agents: `/examples/ml_agents/*.ipynb`
- DS agents: `/examples/ds_agents/*.ipynb`

### External Links
- GitHub: https://github.com/business-science/ai-data-science-team
- PyPI: https://pypi.org/project/ai-data-science-team/
- LangGraph Docs: https://langchain-ai.github.io/langgraph/

---

## Quick Reference

### Available Agents

**Standard Agents**:
- `DataWranglingAgent`: Merge, join, transform data
- `DataVisualizationAgent`: Create Plotly visualizations
- `DataCleaningAgent`: Handle missing values, outliers, types
- `FeatureEngineeringAgent`: Create ML-ready features
- `DataLoaderToolsAgent`: Load CSV, Excel, Parquet, Pickle
- `SQLDatabaseAgent`: Query SQL databases

**ML Agents**:
- `H2OMLAgent`: AutoML with H2O
- `MLflowToolsAgent`: MLflow operations
- `ModelEvaluationAgent`: Model evaluation
- `SurvivalAnalysisAgent`: Time-to-event analysis for cancer research
- `GenomicsAnalysisAgent`: Mutation analysis and pathway enrichment

**DS Agents**:
- `EDAToolsAgent`: Automated EDA with reports

**Multi-Agents**:
- `PandasDataAnalyst`: Wrangling + Visualization
- `SQLDataAnalyst`: SQL + Visualization
- `SupervisorDSTeam`: Orchestrates multiple agents (in development)

### Common Parameters

```python
agent = SomeAgent(
    model=llm,              # Required: LLM instance
    n_samples=30,           # Rows to sample for summaries
    log=False,              # Enable logging
    log_path="logs/",       # Log directory
    file_name="func.py",    # Output filename
    function_name="func",   # Generated function name
    overwrite=True,         # Overwrite existing logs
    human_in_the_loop=False,        # Enable human review
    bypass_recommended_steps=False,  # Skip recommendations
    bypass_explain_code=False,       # Skip explanation
    checkpointer=None       # State checkpointer
)
```

---

## Cancer Research Applications

### Survival Analysis Agent

The **SurvivalAnalysisAgent** (`ml_agents/survival_analysis_agent.py`) is specifically designed for oncology research:

**Key Features**:
- Kaplan-Meier survival curves with confidence intervals
- Cox proportional hazards modeling
- Risk stratification and scoring
- Log-rank test for group comparisons
- Survival predictions for new patients
- Interactive Plotly visualizations

**Use Cases**:
```python
from ai_data_science_team.ml_agents import SurvivalAnalysisAgent

# Initialize agent
survival_agent = SurvivalAnalysisAgent(
    model=llm,
    time_column="survival_months",
    event_column="death_event",
    log=True
)

# Analyze treatment efficacy
survival_agent.invoke_agent(
    data_raw=clinical_data,
    user_instructions="Compare survival between treatment A and B with log-rank test"
)

# Get results
results = survival_agent.get_survival_results()
plot = survival_agent.get_plotly_graph()
```

**Dependencies**:
- `lifelines`: Core survival analysis library
- Install with: `pip install ai-data-science-team[machine_learning]`

**Example Notebook**: `/examples/ml_agents/survival_analysis_agent.ipynb`

**Integration with Cancer Databases**:
- Compatible with TCGA data
- Works with cBioPortal exports
- Supports clinical trial datasets
- HIPAA-compliant when properly configured

**Common Analyses**:
1. **Treatment Comparison**: Compare survival across treatment arms
2. **Prognostic Factors**: Identify variables affecting survival
3. **Risk Stratification**: Group patients by predicted risk
4. **Subgroup Analysis**: Analyze by tumor stage, biomarkers, etc.
5. **Survival Prediction**: Estimate outcomes for new patients

**Tools Available** (`tools/survival.py`):
- `get_survival_data_summary()`: Summarize survival datasets
- `validate_survival_data()`: Check data quality
- `get_survival_analysis_best_practices()`: Coding guidelines

### Genomics Analysis Agent

The **GenomicsAnalysisAgent** (`ml_agents/genomics_analysis_agent.py`) analyzes somatic mutations and performs pathway enrichment:

**Key Features**:
- Driver gene identification (TP53, KRAS, PIK3CA, etc.)
- Mutation type distribution analysis
- Pathway enrichment (RAS/RAF, PI3K/AKT, TP53, DNA repair)
- Tumor mutational burden (TMB) calculation
- Actionable mutation discovery
- Oncoprint-style visualizations

**Use Cases**:
```python
from ai_data_science_team.ml_agents import GenomicsAnalysisAgent

# Initialize agent
genomics_agent = GenomicsAnalysisAgent(
    model=llm,
    gene_column="gene",
    mutation_column="mutation_type",
    log=True
)

# Identify driver genes and pathways
genomics_agent.invoke_agent(
    data_raw=mutation_data,
    user_instructions="Identify driver genes and perform pathway enrichment"
)

# Get results
results = genomics_agent.get_genomics_results()
plot = genomics_agent.get_plotly_graph()
```

**Example Notebook**: `/examples/ml_agents/genomics_analysis_agent.ipynb`

**Tools Available** (`tools/genomics.py`):
- `get_genomics_data_summary()`: Summarize mutation datasets
- `validate_genomics_data()`: Check data quality
- `get_common_cancer_genes()`: List of known driver genes
- `get_cancer_pathways()`: Cancer pathway gene sets
- `calculate_tumor_mutation_burden()`: TMB calculation

**Common Analyses**:
1. **Driver Discovery**: Identify recurrently mutated cancer genes
2. **Pathway Analysis**: Group mutations by biological pathway
3. **TMB Calculation**: Assess immunotherapy eligibility
4. **Actionable Targets**: Find precision medicine opportunities
5. **Clonality Analysis**: VAF-based tumor evolution inference

**Integration with Other Agents**:
```python
# Combine genomics + survival analysis
genomics_agent.invoke_agent(...)  # Find TP53 mutations
survival_agent.invoke_agent(...)   # Compare survival by TP53 status
```

### Future Cancer Research Agents

**Planned Additions**:
- **BiomarkerDiscoveryAgent**: Feature selection, signature development
- **MedicalImagingAgent**: Tumor segmentation, radiomics
- **ClinicalTrialAgent**: Patient stratification, outcome modeling
- **DrugResponseAgent**: Predict treatment response

**Integration Opportunities**:
- **pyBioPortal**: cBioPortal data access
- **GenePioneer**: Essential gene identification
- **Biopython**: Sequence analysis
- **BioPandas**: Molecular structure analysis

---

## Changelog & Version Info

**Current Version**: Beta (pre-0.1.0)

**Recent Updates**:
- Added Genomics Analysis Agent for mutation and pathway analysis
- Added Survival Analysis Agent for cancer research (lifelines integration)
- Added H2O ML Agent with MLflow integration
- Added EDA Tools Agent
- Added Multi-Agent systems (Pandas, SQL)
- Added Data Loader Tools Agent
- Enhanced error recovery with retry logic
- Improved sandboxed code execution

**Upcoming**:
- Supervisor Agent (in planning)
- Interpretability Agent
- More ML agents
- Stable 0.1.0 release

---

## Support & Community

### Reporting Issues
- GitHub Issues: https://github.com/business-science/ai-data-science-team/issues

### Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

### Educational Resources
- Generative AI for Data Scientists Workshop
- Learn more: https://learn.business-science.io/ai-register

### Enterprise Support
- Custom AI Data Science Teams
- Contact: https://www.business-science.io/contact.html

---

**Last Updated**: 2025-12-16
**Maintained By**: Business Science / Matt Dancho
**License**: MIT
