# BUSINESS SCIENCE UNIVERSITY
# AI DATA SCIENCE TEAM
# ***
# OpenRouter Integration Helper

"""
OpenRouter provides cost-effective access to multiple LLM providers.

Benefits:
- 10-100x cheaper than direct OpenAI API
- Access to many models (Claude, Llama, Mistral, etc.)
- Unified API compatible with LangChain
- Pay only for what you use

Setup:
1. Get API key from https://openrouter.ai/
2. Set OPENROUTER_API_KEY environment variable
3. Use get_openrouter_llm() to create LangChain-compatible LLM
"""

import os
from typing import Optional
from langchain_openai import ChatOpenAI


def get_openrouter_llm(
    model: str = "anthropic/claude-3.5-sonnet",
    temperature: float = 0,
    api_key: Optional[str] = None,
    **kwargs
) -> ChatOpenAI:
    """
    Create a LangChain-compatible LLM using OpenRouter.

    OpenRouter provides access to multiple LLM providers at significantly
    lower costs than direct API access. Perfect for cancer research agents
    where cost can accumulate quickly.

    Parameters
    ----------
    model : str
        OpenRouter model identifier. Popular options:

        **Recommended for Cancer Research:**
        - "anthropic/claude-3.5-sonnet" (best quality, ~$3/M tokens)
        - "anthropic/claude-3-haiku" (fast & cheap, ~$0.25/M tokens)
        - "google/gemini-pro-1.5" (good quality, ~$1.25/M tokens)

        **Budget Options:**
        - "meta-llama/llama-3.1-70b-instruct" (~$0.35/M tokens)
        - "mistralai/mistral-7b-instruct" (~$0.07/M tokens)
        - "openchat/openchat-7b" (~$0.07/M tokens)

        **Premium Options:**
        - "openai/gpt-4o" (~$2.5/M tokens)
        - "anthropic/claude-3-opus" (~$15/M tokens)

    temperature : float
        Sampling temperature (0 = deterministic, 1 = creative)
        Default: 0 (recommended for data analysis)

    api_key : str, optional
        OpenRouter API key. If not provided, reads from OPENROUTER_API_KEY
        environment variable.

    **kwargs
        Additional arguments passed to ChatOpenAI:
        - max_tokens: Maximum tokens in response
        - timeout: Request timeout in seconds
        - max_retries: Number of retry attempts

    Returns
    -------
    ChatOpenAI
        LangChain-compatible LLM instance configured for OpenRouter

    Examples
    --------
    >>> import os
    >>> from ai_data_science_team.utils.openrouter import get_openrouter_llm
    >>> from ai_data_science_team.ml_agents import SurvivalAnalysisAgent
    >>>
    >>> # Set API key
    >>> os.environ['OPENROUTER_API_KEY'] = 'sk-or-...'
    >>>
    >>> # Use Claude 3.5 Sonnet (high quality)
    >>> llm = get_openrouter_llm("anthropic/claude-3.5-sonnet")
    >>>
    >>> # Use with cancer research agents
    >>> survival_agent = SurvivalAnalysisAgent(
    ...     model=llm,
    ...     time_column="survival_months",
    ...     event_column="death_event"
    ... )
    >>>
    >>> # Or use budget model for testing
    >>> llm_cheap = get_openrouter_llm("meta-llama/llama-3.1-70b-instruct")
    >>> genomics_agent = GenomicsAnalysisAgent(model=llm_cheap, ...)

    Notes
    -----
    - OpenRouter requires an API key from https://openrouter.ai/
    - Pricing is typically 10-100x cheaper than direct API access
    - Some models have rate limits - check OpenRouter documentation
    - For cancer research, Claude 3.5 Sonnet offers best quality/cost ratio

    See Also
    --------
    get_cost_estimate : Estimate costs for your analysis
    list_available_models : See all available OpenRouter models
    """

    # Get API key
    if api_key is None:
        api_key = os.environ.get("OPENROUTER_API_KEY")

    if not api_key:
        raise ValueError(
            "OpenRouter API key not found. Either:\n"
            "1. Set OPENROUTER_API_KEY environment variable\n"
            "2. Pass api_key parameter\n"
            "\nGet your API key from: https://openrouter.ai/keys"
        )

    # Create LangChain LLM with OpenRouter configuration
    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/business-science/ai-data-science-team",
            "X-Title": "AI Data Science Team - Cancer Research",
        },
        **kwargs
    )

    return llm


def get_cost_estimate(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> dict:
    """
    Estimate costs for OpenRouter API usage.

    Parameters
    ----------
    model : str
        OpenRouter model identifier
    input_tokens : int
        Estimated input tokens
    output_tokens : int
        Estimated output tokens

    Returns
    -------
    dict
        Cost breakdown with estimated total

    Examples
    --------
    >>> estimate = get_cost_estimate(
    ...     "anthropic/claude-3.5-sonnet",
    ...     input_tokens=10000,
    ...     output_tokens=2000
    ... )
    >>> print(f"Estimated cost: ${estimate['total']:.4f}")
    """

    # Approximate pricing (per million tokens)
    # Source: https://openrouter.ai/models (as of Dec 2024)
    pricing = {
        # Anthropic
        "anthropic/claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
        "anthropic/claude-3-haiku": {"input": 0.25, "output": 1.25},
        "anthropic/claude-3-opus": {"input": 15.00, "output": 75.00},

        # Google
        "google/gemini-pro-1.5": {"input": 1.25, "output": 5.00},
        "google/gemini-flash-1.5": {"input": 0.075, "output": 0.30},

        # Meta
        "meta-llama/llama-3.1-70b-instruct": {"input": 0.35, "output": 0.40},
        "meta-llama/llama-3.1-8b-instruct": {"input": 0.07, "output": 0.07},

        # Mistral
        "mistralai/mistral-7b-instruct": {"input": 0.07, "output": 0.07},
        "mistralai/mixtral-8x7b-instruct": {"input": 0.24, "output": 0.24},

        # OpenAI
        "openai/gpt-4o": {"input": 2.50, "output": 10.00},
        "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},

        # Default fallback
        "default": {"input": 1.00, "output": 2.00},
    }

    # Get pricing for model
    model_pricing = pricing.get(model, pricing["default"])

    # Calculate costs
    input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
    output_cost = (output_tokens / 1_000_000) * model_pricing["output"]
    total_cost = input_cost + output_cost

    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total": total_cost,
        "currency": "USD",
    }


def list_recommended_models() -> dict:
    """
    List recommended OpenRouter models for cancer research.

    Returns
    -------
    dict
        Categorized model recommendations with pricing

    Examples
    --------
    >>> models = list_recommended_models()
    >>> print("Premium models:", models['premium'])
    >>> print("Budget models:", models['budget'])
    """

    return {
        "premium": {
            "anthropic/claude-3.5-sonnet": {
                "price": "$3/M tokens",
                "quality": "⭐⭐⭐⭐⭐",
                "use_case": "Production cancer research",
                "pros": "Best quality, excellent for complex genomics",
            },
            "anthropic/claude-3-opus": {
                "price": "$15/M tokens",
                "quality": "⭐⭐⭐⭐⭐",
                "use_case": "Critical clinical decisions",
                "pros": "Highest quality, most accurate",
            },
        },
        "balanced": {
            "anthropic/claude-3-haiku": {
                "price": "$0.25/M tokens",
                "quality": "⭐⭐⭐⭐",
                "use_case": "Fast iterations, testing",
                "pros": "Very fast, cheap, still high quality",
            },
            "google/gemini-pro-1.5": {
                "price": "$1.25/M tokens",
                "quality": "⭐⭐⭐⭐",
                "use_case": "General cancer research",
                "pros": "Good balance of cost and performance",
            },
        },
        "budget": {
            "meta-llama/llama-3.1-70b-instruct": {
                "price": "$0.35/M tokens",
                "quality": "⭐⭐⭐",
                "use_case": "Development and prototyping",
                "pros": "Open source, very cheap",
            },
            "google/gemini-flash-1.5": {
                "price": "$0.075/M tokens",
                "quality": "⭐⭐⭐",
                "use_case": "High-volume testing",
                "pros": "Extremely cheap, fast",
            },
        },
    }


def compare_costs(
    openai_model: str = "gpt-4o",
    openrouter_model: str = "anthropic/claude-3.5-sonnet",
    tokens: int = 100000,
) -> None:
    """
    Compare costs between direct OpenAI and OpenRouter.

    Parameters
    ----------
    openai_model : str
        OpenAI model name
    openrouter_model : str
        OpenRouter model identifier
    tokens : int
        Number of tokens to compare

    Examples
    --------
    >>> compare_costs(tokens=1_000_000)  # 1M tokens
    """

    # Simplified comparison
    openai_costs = {
        "gpt-4o": 5.00,  # Average per M tokens
        "gpt-4o-mini": 0.375,
    }

    openrouter_estimate = get_cost_estimate(
        openrouter_model,
        input_tokens=tokens // 2,
        output_tokens=tokens // 2,
    )

    openai_cost = (tokens / 1_000_000) * openai_costs.get(openai_model, 5.00)

    savings = openai_cost - openrouter_estimate["total"]
    savings_pct = (savings / openai_cost) * 100 if openai_cost > 0 else 0

    print(f"\n{'='*60}")
    print(f"Cost Comparison for {tokens:,} tokens")
    print(f"{'='*60}")
    print(f"\nDirect OpenAI ({openai_model}):")
    print(f"  Cost: ${openai_cost:.4f}")
    print(f"\nOpenRouter ({openrouter_model}):")
    print(f"  Cost: ${openrouter_estimate['total']:.4f}")
    print(f"\nSavings:")
    print(f"  ${savings:.4f} ({savings_pct:.1f}% cheaper)")
    print(f"{'='*60}\n")
