# LangChain + AI Data Analysis Integration Design

## Lumen Trading Analytics — AI-Powered Analysis Layer

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Analysis](#2-current-state-analysis)
3. [Claude Subscription vs API — The Hard Truth](#3-claude-subscription-vs-api--the-hard-truth)
4. [Recommended Solution Architecture](#4-recommended-solution-architecture)
5. [Solution A: MCP Server (Claude Subscription)](#5-solution-a-mcp-server-claude-subscription)
6. [Solution B: LangChain + Ollama (Free, Automated)](#6-solution-b-langchain--ollama-free-automated)
7. [Solution C: LangChain + Claude API (Pay-Per-Use)](#7-solution-c-langchain--claude-api-pay-per-use)
8. [AI Analysis Capabilities](#8-ai-analysis-capabilities)
9. [Implementation Roadmap](#9-implementation-roadmap)
10. [Appendix: Cost Comparison](#10-appendix-cost-comparison)

---

## 1. Executive Summary

This document proposes integrating AI-powered analysis into Lumen to enable natural-language
trend discovery, anomaly detection, and strategy crafting on trading data. Three solution paths
are evaluated, with a **primary recommendation of building an MCP (Model Context Protocol)
server** that connects Claude Desktop (subscription) directly to Lumen's data and analytics
engines.

### Key Findings

| Approach | Uses Subscription? | Cost | Quality | Automation |
|----------|-------------------|------|---------|------------|
| **MCP Server** | Yes (Pro/Max $20-100/mo) | Flat monthly | Highest (Claude) | Interactive only |
| **LangChain + Ollama** | N/A (local LLM) | $0 (hardware only) | Good (DeepSeek/Llama) | Full automation |
| **LangChain + Claude API** | No (separate billing) | ~$10-200/mo | Highest (Claude) | Full automation |

**Primary recommendation:** Build an MCP server (Solution A) as the main path — it uses your
existing Claude subscription, provides the highest quality analysis, and is the most natural
integration point. Supplement with Solution B (Ollama) for automated batch analysis pipelines
where interactive use isn't needed.

---

## 2. Current State Analysis

### What Lumen Already Has

Lumen is a sophisticated PyQt6 desktop application with powerful quantitative analytics:

**Core Analytics Engines:**
- `MetricsCalculator` — 25 trading metrics (win rate, Kelly, EV, edge, drawdowns, streaks)
- `FeatureAnalyzer` — Multi-criteria feature importance ranking with bootstrap validation
- `MonteCarloEngine` — 5,000-50,000 simulation runs for robustness testing
- `ParameterSensitivityEngine` — Neighborhood and sweep analysis for optimization
- `EquityCalculator` — Flat-stake and Kelly-compounded equity curves
- `StatisticsCalculator` — 7 analytical tables (MAE, MFE, stop loss, offset, scaling, etc.)
- `PortfolioMetricsCalculator` — Sharpe, Sortino, Calmar, VaR, CVaR, correlation analysis

**Data Architecture:**
- In-memory pandas DataFrames (no SQL database)
- Parquet caching for performance
- Signal-driven state management via `AppState`
- Trade data: ticker, date, time, gain%, MAE%, MFE%, plus arbitrary feature columns

**What's Missing:**
- No AI/ML integration of any kind
- No natural language querying
- No automated insight generation
- No trend/anomaly narratives — users must interpret raw numbers themselves

### The Gap AI Fills

The user currently must:
1. Load data → manually inspect metrics → mentally identify patterns
2. Run Monte Carlo → interpret percentile bands manually
3. Run feature analysis → read feature rankings and ranges → mentally synthesize
4. Compare parameter sensitivity results → decide optimal parameters manually

An AI layer would **synthesize across all these engines** and produce actionable narratives:
- "Your strategy shows regime change — win rate dropped from 68% to 52% in the last 30 days"
- "Feature X (RSI 14) between 35-55 produces 2.3x better EV than baseline with 95% confidence"
- "Monte Carlo shows 12% ruin probability at current Kelly — reducing to 15% fractional Kelly
  drops this to 2.1%"

---

## 3. Claude Subscription vs API — The Hard Truth

### They Are Completely Separate Products

| | Claude Pro/Max Subscription | Claude API |
|---|---|---|
| **Access** | claude.ai (web, desktop, mobile) | console.anthropic.com |
| **Billing** | $20/month (Pro) or $100/month (Max) | Pay-per-token |
| **Programmatic access** | No — cannot call from code | Yes — full SDK/REST |
| **LangChain compatible** | No | Yes |
| **MCP compatible** | Yes (via Claude Desktop) | Yes (via SDK) |
| **Authentication** | Email/password login | API key |

**Bottom line:** LangChain requires the API. Your monthly subscription cannot be used with
LangChain. However, **MCP bridges this gap** — it lets Claude Desktop (your subscription)
connect to custom data sources and tools, effectively giving you programmatic-level analysis
through an interactive interface.

### Why MCP Is the Answer for Subscription Users

MCP (Model Context Protocol) is Anthropic's open standard for connecting AI models to external
tools. As of 2026, it has become the industry standard (adopted by OpenAI, Google, Microsoft).

When you build an MCP server for Lumen:
1. Claude Desktop discovers it on startup
2. You can ask Claude questions in natural language
3. Claude calls your MCP tools to access Lumen's data and engines
4. Claude synthesizes results into actionable analysis
5. All powered by your existing Pro/Max subscription — no API key needed

---

## 4. Recommended Solution Architecture

### Hybrid Architecture (Best of Both Worlds)

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERACTIVE ANALYSIS                       │
│                                                               │
│  Claude Desktop (Pro/Max subscription)                       │
│       │                                                       │
│       ▼                                                       │
│  ┌─────────────────────┐                                     │
│  │  Lumen MCP Server   │◄── Exposes data + analytics tools   │
│  │  (Solution A)       │                                     │
│  └────────┬────────────┘                                     │
│           │                                                   │
│           ▼                                                   │
│  ┌─────────────────────┐                                     │
│  │  Lumen Core Engines │                                     │
│  │  • MetricsCalc      │                                     │
│  │  • FeatureAnalyzer  │                                     │
│  │  • MonteCarlo       │                                     │
│  │  • Statistics        │                                     │
│  │  • Equity           │                                     │
│  └─────────────────────┘                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                   AUTOMATED ANALYSIS                          │
│                                                               │
│  Ollama (DeepSeek-V3 / Llama 3.2)   ─── $0 cost             │
│       │                                                       │
│       ▼                                                       │
│  ┌─────────────────────┐                                     │
│  │  LangChain Agent    │◄── Pandas DataFrame Agent            │
│  │  (Solution B)       │                                     │
│  └────────┬────────────┘                                     │
│           │                                                   │
│           ▼                                                   │
│  ┌─────────────────────┐                                     │
│  │  Lumen Core Engines │  (same engines, accessed via Python) │
│  └─────────────────────┘                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Solution A: MCP Server (Claude Subscription)

### Overview

Build a standalone MCP server that exposes Lumen's trading data and analytics engines as tools
that Claude Desktop can call. This runs as a local process alongside Lumen.

### Architecture

```
Claude Desktop
    │
    │ (MCP Protocol over stdio)
    │
    ▼
lumen-mcp-server (Python process)
    │
    ├── Tools (callable by Claude):
    │   ├── load_data(file_path) → summary stats
    │   ├── get_metrics(filters?) → 25 trading metrics
    │   ├── get_equity_curve(mode, filters?) → equity data
    │   ├── analyze_features(top_n?) → ranked features + ranges
    │   ├── run_monte_carlo(config?) → simulation results
    │   ├── get_statistics_table(table_name) → analytical table
    │   ├── compare_filters(filter_a, filter_b) → side-by-side metrics
    │   ├── get_trade_distribution(column) → histogram data
    │   ├── scan_anomalies(lookback_days?) → anomaly report
    │   ├── suggest_strategy(objective?) → strategy recommendations
    │   └── get_portfolio_metrics(strategies) → portfolio analysis
    │
    ├── Resources (readable by Claude):
    │   ├── lumen://data/summary → current dataset summary
    │   ├── lumen://metrics/baseline → baseline metrics snapshot
    │   ├── lumen://metrics/filtered → filtered metrics snapshot
    │   └── lumen://config/current → current configuration
    │
    └── Prompts (reusable templates):
        ├── daily_analysis → end-of-day strategy review
        ├── anomaly_scan → detect unusual patterns
        ├── strategy_builder → construct new strategy from data
        └── risk_assessment → comprehensive risk report
```

### MCP Server Implementation

```python
# src/mcp/server.py — Lumen MCP Server

from mcp.server import Server
from mcp.types import Tool, TextContent, Resource
import pandas as pd
import json

from src.core.metrics import MetricsCalculator
from src.core.feature_analyzer import FeatureAnalyzer
from src.core.monte_carlo import MonteCarloEngine, MonteCarloConfig
from src.core.statistics import StatisticsCalculator
from src.core.models import AdjustmentParams, ColumnMapping
from src.core.file_loader import FileLoader

app = Server("lumen-analytics")

# Global state for the MCP session
_state = {
    "df": None,
    "column_mapping": None,
    "baseline_metrics": None,
}


@app.tool()
async def load_data(file_path: str) -> str:
    """Load a trading data file (CSV, Excel, Parquet) and return summary statistics.

    Args:
        file_path: Absolute path to the data file.
    """
    loader = FileLoader()
    df = loader.load(file_path)
    _state["df"] = df

    summary = {
        "rows": len(df),
        "columns": list(df.columns),
        "date_range": f"{df.iloc[:, 1].min()} to {df.iloc[:, 1].max()}" if len(df) > 0 else "N/A",
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "sample_rows": df.head(5).to_dict(orient="records"),
        "null_counts": df.isnull().sum().to_dict(),
    }
    return json.dumps(summary, indent=2, default=str)


@app.tool()
async def get_metrics(
    stop_loss: float = 8.0,
    efficiency: float = 5.0,
    flat_stake: float = 10000.0,
    starting_capital: float = 100000.0,
    fractional_kelly: float = 25.0,
) -> str:
    """Calculate all 25 trading metrics for the loaded dataset.

    Returns win rate, EV, Kelly criterion, edge, drawdowns, streaks, and more.
    """
    df = _state["df"]
    mapping = _state["column_mapping"]
    if df is None or mapping is None:
        return "Error: No data loaded. Use load_data first."

    calc = MetricsCalculator()
    params = AdjustmentParams(stop_loss=stop_loss, efficiency=efficiency)
    metrics, _, _ = calc.calculate(
        df=df,
        gain_col=mapping.gain_pct,
        mae_col=mapping.mae_pct,
        adjustment_params=params,
        derived=True,
        date_col=mapping.date,
        time_col=mapping.time,
        flat_stake=flat_stake,
        start_capital=starting_capital,
        fractional_kelly_pct=fractional_kelly,
    )
    _state["baseline_metrics"] = metrics

    from dataclasses import asdict
    return json.dumps(asdict(metrics), indent=2, default=str)


@app.tool()
async def analyze_features(top_n: int = 10) -> str:
    """Rank features by their impact on trading gains.

    Uses mutual information, rank correlation, and conditional variance.
    Returns top N features with favorable/unfavorable ranges and confidence intervals.
    """
    df = _state["df"]
    mapping = _state["column_mapping"]
    if df is None or mapping is None:
        return "Error: No data loaded."

    analyzer = FeatureAnalyzer()
    results = analyzer.analyze(
        df=df,
        gain_col=mapping.gain_pct,
        exclude_cols=[mapping.ticker, mapping.date, mapping.time,
                      mapping.gain_pct, mapping.mae_pct, mapping.mfe_pct],
    )
    # Serialize top N results
    output = []
    for r in results[:top_n]:
        output.append({
            "feature": r.feature_name,
            "impact_score": round(r.impact_score, 2),
            "ranges": [
                {
                    "range": rng.range_label,
                    "classification": rng.classification.value,
                    "trade_count": rng.trade_count,
                    "ev": round(rng.ev, 4) if rng.ev else None,
                    "win_rate": round(rng.win_rate, 2) if rng.win_rate else None,
                    "p_value": round(rng.p_value, 4) if rng.p_value else None,
                }
                for rng in r.ranges
            ],
        })
    return json.dumps(output, indent=2)


@app.tool()
async def run_monte_carlo(
    num_simulations: int = 5000,
    initial_capital: float = 100000.0,
    ruin_threshold_pct: float = 50.0,
) -> str:
    """Run Monte Carlo simulation to test strategy robustness.

    Returns equity curve percentile bands, risk of ruin, max drawdown distribution,
    and VaR/CVaR metrics.
    """
    df = _state["df"]
    mapping = _state["column_mapping"]
    if df is None or mapping is None:
        return "Error: No data loaded."

    config = MonteCarloConfig(
        num_simulations=num_simulations,
        initial_capital=initial_capital,
        ruin_threshold_pct=ruin_threshold_pct,
    )
    engine = MonteCarloEngine()
    gains = df[mapping.gain_pct].astype(float).values
    results = engine.run(gains, config)

    output = {
        "probability_of_ruin": round(results.probability_of_ruin * 100, 2),
        "median_final_equity": round(results.median_final_equity, 2),
        "percentile_5_equity": round(results.percentile_5_equity, 2),
        "percentile_95_equity": round(results.percentile_95_equity, 2),
        "median_max_drawdown_pct": round(results.median_max_drawdown_pct, 2),
        "var_95": round(results.var_95, 2),
        "cvar_95": round(results.cvar_95, 2),
    }
    return json.dumps(output, indent=2)


@app.tool()
async def scan_anomalies(
    lookback_days: int = 30,
    z_score_threshold: float = 2.0,
) -> str:
    """Scan for anomalies in recent trading data.

    Detects: regime changes in win rate, unusual drawdown patterns,
    outlier gains/losses, streak anomalies, and volume shifts.
    """
    # Implementation would analyze recent data windows vs historical
    # This is a new capability built on top of existing engines
    df = _state["df"]
    mapping = _state["column_mapping"]
    if df is None or mapping is None:
        return "Error: No data loaded."

    # ... anomaly detection logic using rolling windows,
    # z-scores, and comparison to historical distributions
    return json.dumps({"anomalies": [], "summary": "Implementation pending"})


@app.tool()
async def suggest_strategy(
    objective: str = "maximize_ev",
    risk_tolerance: str = "moderate",
) -> str:
    """Generate strategy recommendations based on data analysis.

    Combines feature analysis, parameter sensitivity, and Monte Carlo
    to suggest optimal filter combinations, position sizing, and stop levels.

    Args:
        objective: One of 'maximize_ev', 'maximize_kelly', 'minimize_drawdown',
                   'maximize_sharpe'.
        risk_tolerance: One of 'conservative', 'moderate', 'aggressive'.
    """
    # Would orchestrate multiple engines to build strategy
    return json.dumps({"recommendations": [], "summary": "Implementation pending"})


# Resource definitions for Claude to read context
@app.resource("lumen://data/summary")
async def get_data_summary() -> str:
    """Current dataset summary including shape, columns, and basic stats."""
    df = _state["df"]
    if df is None:
        return "No data loaded."
    return df.describe().to_string()
```

### Claude Desktop Configuration

Add to `~/.config/Claude/claude_desktop_config.json` (or equivalent on your OS):

```json
{
  "mcpServers": {
    "lumen-analytics": {
      "command": "python",
      "args": ["-m", "src.mcp.server"],
      "cwd": "/path/to/Lumen",
      "env": {
        "PYTHONPATH": "/path/to/Lumen"
      }
    }
  }
}
```

### What You Can Ask Claude Desktop

Once the MCP server is running, you open Claude Desktop and have conversations like:

> **You:** Load my trading data from C:/Users/me/trades_2025.csv and give me a full analysis

> **Claude:** *[calls load_data, get_metrics, analyze_features]*
> Here's your analysis of 15,432 trades from Jan-Dec 2025:
>
> **Performance Summary:** 61.3% win rate, EV of 0.42%, Kelly suggests 18.7% position sizing.
> Your edge is +6,487% cumulative across all trades.
>
> **Top Insights:**
> 1. RSI_14 between 35-55 produces EV of 0.71% vs baseline 0.42% (p=0.003)
> 2. Trades taken before 10:30 AM have 8% higher win rate
> 3. Your strategy underperforms on Fridays (EV: -0.12% vs +0.52% other days)
>
> **Risk Assessment:** Monte Carlo shows 4.2% probability of 50% drawdown...

> **You:** I noticed my win rate has been dropping. Can you check for regime changes in the
> last 60 days vs the prior period?

> **Claude:** *[calls scan_anomalies with lookback_days=60]*
> You're right to be concerned. Here's what I found...

### Advantages of MCP Approach

1. **Uses your existing subscription** — no additional API costs
2. **Highest quality** — Claude Opus/Sonnet via Desktop, not a local model
3. **Conversational** — follow-up questions, refine analysis interactively
4. **Secure** — data stays local, MCP runs on your machine
5. **Extensible** — add new tools as you build new Lumen features
6. **Industry standard** — MCP adopted by all major AI providers (2025-2026)

### Limitations

1. **Interactive only** — cannot be automated/scripted (requires manual prompting)
2. **No batch processing** — each analysis session is manual
3. **No integration into Lumen UI** — analysis happens in Claude Desktop, not in the app

---

## 6. Solution B: LangChain + Ollama (Free, Automated)

### Overview

For automated analysis pipelines (scheduled reports, batch anomaly detection, strategy
backtesting), use LangChain with a locally-hosted open-source LLM via Ollama. This costs $0
beyond hardware.

### Architecture

```
┌─────────────────────────────────────┐
│         Lumen PyQt6 App              │
│                                      │
│  ┌──────────────┐  ┌──────────────┐ │
│  │ AI Insights  │  │ Strategy     │ │
│  │ Tab (new)    │  │ Advisor Tab  │ │
│  └──────┬───────┘  └──────┬───────┘ │
│         │                  │         │
│         ▼                  ▼         │
│  ┌─────────────────────────────────┐ │
│  │     Analysis Orchestrator       │ │
│  │  (LangChain Agent Manager)      │ │
│  └──────────────┬──────────────────┘ │
│                 │                     │
│    ┌────────────┼────────────┐       │
│    ▼            ▼            ▼       │
│ ┌──────┐  ┌──────────┐  ┌────────┐  │
│ │Trend │  │ Anomaly  │  │Strategy│  │
│ │Agent │  │ Agent    │  │Agent   │  │
│ └──┬───┘  └────┬─────┘  └───┬────┘  │
│    │           │             │        │
│    └───────────┼─────────────┘        │
│                ▼                      │
│  ┌─────────────────────────────────┐ │
│  │  Lumen Core Engines (existing)  │ │
│  │  MetricsCalc | FeatureAnalyzer  │ │
│  │  MonteCarlo  | Statistics       │ │
│  └─────────────────────────────────┘ │
└─────────────────────────────────────┘
         │
         ▼
   ┌───────────┐
   │  Ollama   │  (DeepSeek-V3.2 / Llama 3.2 / Mistral)
   │  (local)  │  Running at localhost:11434
   └───────────┘
```

### Dependencies to Add

```toml
# pyproject.toml additions
[project.optional-dependencies]
ai = [
    "langchain>=0.3.0",
    "langchain-ollama>=0.3.0",
    "langchain-experimental>=0.3.0",
    "langchain-community>=0.3.0",
]
```

### Core Implementation

```python
# src/ai/orchestrator.py — Analysis Orchestrator

from langchain_ollama import ChatOllama
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain.agents import AgentType
from langchain_core.prompts import ChatPromptTemplate
import pandas as pd

from src.core.metrics import MetricsCalculator
from src.core.feature_analyzer import FeatureAnalyzer
from src.core.models import AdjustmentParams


class AnalysisOrchestrator:
    """Orchestrates AI-powered analysis using LangChain + Ollama."""

    def __init__(self, model_name: str = "deepseek-v3:latest"):
        self.llm = ChatOllama(
            model=model_name,
            temperature=0,       # Deterministic for analysis
            num_ctx=32768,       # Large context for data
        )
        self._metrics_calc = MetricsCalculator()
        self._feature_analyzer = FeatureAnalyzer()

    def create_dataframe_agent(self, df: pd.DataFrame):
        """Create a pandas DataFrame agent for natural language queries."""
        return create_pandas_dataframe_agent(
            self.llm,
            df,
            agent_type="tool-calling",
            allow_dangerous_code=True,
            verbose=True,
            prefix=TRADING_ANALYSIS_PREFIX,  # Custom system prompt
        )

    def analyze_trends(self, df: pd.DataFrame, gain_col: str,
                       date_col: str, window: int = 20) -> dict:
        """Detect trends using rolling statistics + LLM interpretation."""
        # 1. Compute rolling metrics (pure Python — fast, deterministic)
        df_sorted = df.sort_values(date_col)
        gains = df_sorted[gain_col].astype(float)

        rolling_wr = gains.rolling(window).apply(lambda x: (x > 0).mean() * 100)
        rolling_ev = gains.rolling(window).mean() * 100
        rolling_std = gains.rolling(window).std() * 100

        trend_data = {
            "rolling_win_rate": rolling_wr.dropna().tolist()[-10:],
            "rolling_ev": rolling_ev.dropna().tolist()[-10:],
            "rolling_volatility": rolling_std.dropna().tolist()[-10:],
            "current_vs_mean_wr": float(rolling_wr.iloc[-1] - rolling_wr.mean()),
            "current_vs_mean_ev": float(rolling_ev.iloc[-1] - rolling_ev.mean()),
            "wr_trend": "improving" if rolling_wr.iloc[-1] > rolling_wr.iloc[-window] else "declining",
            "ev_trend": "improving" if rolling_ev.iloc[-1] > rolling_ev.iloc[-window] else "declining",
        }

        # 2. LLM interprets the computed data
        prompt = ChatPromptTemplate.from_messages([
            ("system", TREND_ANALYSIS_SYSTEM_PROMPT),
            ("human", f"Analyze these trading trend metrics:\n{trend_data}"),
        ])
        chain = prompt | self.llm
        interpretation = chain.invoke({})

        return {
            "data": trend_data,
            "interpretation": interpretation.content,
        }

    def detect_anomalies(self, df: pd.DataFrame, gain_col: str,
                         date_col: str, z_threshold: float = 2.0) -> dict:
        """Detect statistical anomalies in trading data."""
        gains = df[gain_col].astype(float)
        mean = gains.mean()
        std = gains.std()

        # Z-score based anomaly detection
        z_scores = ((gains - mean) / std).abs()
        anomalies = df[z_scores > z_threshold].copy()
        anomalies["z_score"] = z_scores[z_scores > z_threshold]

        # Streak anomalies
        winners = gains > 0
        streaks = (winners != winners.shift()).cumsum()
        streak_lengths = winners.groupby(streaks).transform("count")
        max_expected_streak = int(3 + 2 * (gains > 0).mean() * 10)  # heuristic
        streak_anomalies = df[streak_lengths > max_expected_streak]

        # Rolling regime detection
        window = min(50, len(df) // 4)
        if window > 10:
            rolling_mean = gains.rolling(window).mean()
            rolling_std_val = gains.rolling(window).std()
            regime_shifts = ((rolling_mean.diff().abs() / rolling_std_val) > 1.5).sum()
        else:
            regime_shifts = 0

        anomaly_data = {
            "outlier_trades": len(anomalies),
            "outlier_pct": round(len(anomalies) / len(df) * 100, 2),
            "worst_outliers": anomalies.nlargest(5, "z_score")[
                [date_col, gain_col, "z_score"]
            ].to_dict("records") if len(anomalies) > 0 else [],
            "streak_anomalies": len(streak_anomalies),
            "regime_shift_signals": int(regime_shifts),
        }

        # LLM interpretation
        prompt = ChatPromptTemplate.from_messages([
            ("system", ANOMALY_DETECTION_SYSTEM_PROMPT),
            ("human", f"Analyze these anomaly findings:\n{anomaly_data}"),
        ])
        chain = prompt | self.llm
        interpretation = chain.invoke({})

        return {
            "data": anomaly_data,
            "interpretation": interpretation.content,
        }

    def craft_strategy(self, df: pd.DataFrame, mapping, params,
                       objective: str = "maximize_ev") -> dict:
        """Generate strategy recommendations by combining all engines."""
        # 1. Run feature analysis
        features = self._feature_analyzer.analyze(
            df=df,
            gain_col=mapping.gain_pct,
            exclude_cols=[mapping.ticker, mapping.date, mapping.time,
                         mapping.gain_pct, mapping.mae_pct, mapping.mfe_pct],
        )

        # 2. Get baseline metrics
        metrics, _, _ = self._metrics_calc.calculate(
            df=df, gain_col=mapping.gain_pct, derived=True,
            adjustment_params=params, mae_col=mapping.mae_pct,
            date_col=mapping.date, time_col=mapping.time,
        )

        # 3. Compile analysis context for LLM
        context = {
            "num_trades": metrics.num_trades,
            "win_rate": metrics.win_rate,
            "ev": metrics.ev,
            "kelly": metrics.kelly,
            "edge": metrics.edge,
            "max_dd_pct": metrics.flat_stake_max_dd_pct,
            "top_features": [
                {
                    "name": f.feature_name,
                    "score": f.impact_score,
                    "favorable_ranges": [
                        r.range_label for r in f.ranges
                        if r.classification.value == "favorable"
                    ],
                }
                for f in features[:5]
            ],
            "objective": objective,
        }

        # 4. LLM generates strategy
        prompt = ChatPromptTemplate.from_messages([
            ("system", STRATEGY_GENERATION_SYSTEM_PROMPT),
            ("human", f"Generate a trading strategy based on:\n{context}"),
        ])
        chain = prompt | self.llm
        strategy = chain.invoke({})

        return {
            "context": context,
            "strategy": strategy.content,
        }


# System prompts optimized for trading analysis
TRADING_ANALYSIS_PREFIX = """You are a quantitative trading analyst embedded in the Lumen
analytics platform. You have access to a pandas DataFrame containing historical trading data.
Each row represents one trade with columns for ticker, date, time, gain percentage, MAE
(Maximum Adverse Excursion), and MFE (Maximum Favorable Excursion).

When analyzing data:
- Use precise statistical language
- Always consider sample size when drawing conclusions
- Distinguish between statistical significance and practical significance
- Frame findings in terms of actionable trading decisions
- Express percentages to 2 decimal places
- Flag potential data quality issues if detected
"""

TREND_ANALYSIS_SYSTEM_PROMPT = """You are a trading trend analyst. Given computed rolling
statistics, identify:
1. Direction and strength of trend (improving/declining/stable)
2. Whether current performance deviates significantly from historical mean
3. Potential regime changes (structural breaks in the data)
4. Seasonality or cyclical patterns if visible
5. Actionable recommendations based on trend direction

Be concise and quantitative. Cite specific numbers."""

ANOMALY_DETECTION_SYSTEM_PROMPT = """You are a trading anomaly detection specialist. Given
statistical anomaly data, provide:
1. Classification of each anomaly type (outlier, regime shift, streak)
2. Severity assessment (informational, warning, critical)
3. Possible explanations (market conditions, data quality, strategy drift)
4. Whether anomalies suggest the strategy needs adjustment
5. Recommended actions

Prioritize anomalies by their potential impact on strategy performance."""

STRATEGY_GENERATION_SYSTEM_PROMPT = """You are a quantitative strategy advisor. Given trading
metrics and feature analysis results, generate:
1. Specific filter recommendations (which features to filter, exact ranges)
2. Position sizing guidance based on Kelly criterion and risk tolerance
3. Stop loss optimization suggestions
4. Expected improvement quantified where possible
5. Risk warnings and caveats

Base recommendations ONLY on the data provided. Never hallucinate statistics.
State confidence levels for each recommendation."""
```

### Ollama Setup

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull recommended models (choose based on hardware)
ollama pull deepseek-v3       # Best quality (needs 48GB+ VRAM or high RAM)
ollama pull llama3.2          # Good balance (16GB VRAM)
ollama pull mistral           # Lightweight (8GB VRAM)
ollama pull qwen3:14b         # Strong reasoning (16GB VRAM)
```

### Advantages

1. **$0 cost** — runs entirely locally
2. **Full automation** — can be scheduled, scripted, embedded in Lumen UI
3. **Privacy** — data never leaves your machine
4. **Customizable** — fine-tune models on your specific trading vocabulary

### Limitations

1. **Lower quality** than Claude — especially for nuanced strategy advice
2. **Hardware requirements** — needs decent GPU (8-48GB VRAM depending on model)
3. **Slower** — local inference is slower than cloud API
4. **No conversational follow-up** unless you build a chat interface

---

## 7. Solution C: LangChain + Claude API (Pay-Per-Use)

### Overview

If you decide the quality difference justifies the cost, LangChain works directly with the
Claude API. This is the most powerful automated option but requires separate API billing.

### Cost Optimization

| Technique | Savings | How |
|-----------|---------|-----|
| Use Haiku 4.5 for simple queries | 80% vs Sonnet | Model routing |
| Prompt caching | 90% on repeated context | Cache system prompts |
| Batch API | 50% on non-urgent analysis | Async processing |
| Combined | 75-95% total reduction | All techniques |

**Realistic monthly cost estimate for Lumen analysis:**
- 10 analysis sessions/day × 20 working days = 200 sessions
- ~2,000 tokens per session (input) + ~1,000 tokens output
- Using Haiku 4.5: 200 × 2K × $1/1M + 200 × 1K × $5/1M = $1.40/month
- Using Sonnet 4.5: 200 × 2K × $3/1M + 200 × 1K × $15/1M = $4.20/month

Even heavy usage would likely cost less than $50/month.

### Implementation

```python
# src/ai/claude_provider.py — Claude API Provider

from langchain_anthropic import ChatAnthropic

class ClaudeProvider:
    """LangChain provider for Claude API with cost optimization."""

    def __init__(self, api_key: str, default_model: str = "claude-haiku-4-5-20251101"):
        self.models = {
            "fast": ChatAnthropic(
                model="claude-haiku-4-5-20251101",
                api_key=api_key,
                temperature=0,
            ),
            "balanced": ChatAnthropic(
                model="claude-sonnet-4-5-20251101",
                api_key=api_key,
                temperature=0,
            ),
            "best": ChatAnthropic(
                model="claude-opus-4-5-20251101",
                api_key=api_key,
                temperature=0,
            ),
        }

    def get_model(self, complexity: str = "fast"):
        """Route to appropriate model based on task complexity."""
        return self.models.get(complexity, self.models["fast"])
```

---

## 8. AI Analysis Capabilities

### 8.1 Trend Detection

**What it does:** Identifies directional changes in strategy performance over time.

**Techniques leveraging existing Lumen engines:**

| Technique | Lumen Engine Used | AI Layer Adds |
|-----------|------------------|---------------|
| Rolling metric windows | MetricsCalculator (run on time slices) | Narrative interpretation |
| Feature drift detection | FeatureAnalyzer (run on recent vs historical) | Change significance |
| Equity curve slope analysis | EquityCalculator | Regime classification |
| Seasonal decomposition | New (pandas rolling + scipy) | Pattern explanation |
| Win rate momentum | MetricsCalculator (rolling win rate) | Actionable alerts |

**Example output:**
```
TREND ANALYSIS — Last 30 Days vs Prior 90 Days
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Win Rate:     64.2% → 57.8%   ▼ -6.4pp   ⚠️  DECLINING
EV:           0.48% → 0.31%   ▼ -35.4%   ⚠️  DECLINING
Avg Winner:   1.82% → 1.65%   ▼ -9.3%    ── STABLE
Avg Loser:   -1.21% → -1.34%  ▼ -10.7%   ⚠️  WIDENING LOSSES
Kelly:        22.1% → 14.3%   ▼ -35.3%   🔴 SIGNIFICANT DROP

INTERPRETATION: Your strategy is experiencing a regime shift. The declining
win rate combined with widening average losses suggests either market conditions
have changed or your entry criteria have drifted. The Kelly criterion drop from
22% to 14% means your optimal position size should be reduced by ~35%.

RECOMMENDATION: Tighten stop loss from 8% to 6% and reduce fractional Kelly
from 25% to 15% until win rate stabilizes above 60%.
```

### 8.2 Anomaly Detection

**What it does:** Flags unusual patterns that deviate from historical norms.

**Detection methods:**

1. **Statistical outliers** — Z-score > 2σ on individual trade gains
2. **Streak anomalies** — Win/loss streaks exceeding expected length given win rate
3. **Regime shifts** — CUSUM or rolling mean breakpoint detection
4. **Distribution shifts** — Kolmogorov-Smirnov test on recent vs historical gain distributions
5. **Drawdown anomalies** — Current drawdown vs Monte Carlo expected drawdown distribution
6. **Feature drift** — Top feature ranges shifting (feature X no longer favorable)
7. **Correlation breaks** — Portfolio strategy correlations changing

**Implementation leveraging existing engines:**

```python
# The anomaly detector combines multiple Lumen engines:

class AnomalyDetector:
    def full_scan(self, df, mapping, params):
        # 1. Compare recent metrics to baseline (MetricsCalculator)
        recent = df.tail(100)
        historical = df.head(len(df) - 100)
        recent_metrics = self.calc.calculate(recent, ...)
        hist_metrics = self.calc.calculate(historical, ...)

        # 2. Check if recent is within Monte Carlo expected range
        mc_results = self.mc_engine.run(historical_gains, config)
        # Is current drawdown within the 95th percentile band?

        # 3. Feature stability check (FeatureAnalyzer)
        recent_features = self.feature_analyzer.analyze(recent, ...)
        hist_features = self.feature_analyzer.analyze(historical, ...)
        # Did any feature rankings change significantly?

        # 4. LLM synthesizes all findings into narrative
        ...
```

### 8.3 Strategy Crafting

**What it does:** Generates actionable trading strategies by combining insights from all engines.

**Strategy generation pipeline:**

```
Step 1: Feature Analysis → Identify highest-impact features and favorable ranges
Step 2: Filter Optimization → Test combinations of favorable feature ranges
Step 3: Parameter Sensitivity → Find optimal stop loss and efficiency for filtered set
Step 4: Monte Carlo Validation → Verify strategy robustness under randomization
Step 5: Portfolio Integration → Check if strategy improves overall portfolio metrics
Step 6: LLM Synthesis → Generate human-readable strategy document with rationale
```

**Example output:**
```
STRATEGY RECOMMENDATION: "Momentum RSI Filter"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FILTERS:
  1. RSI_14: 35 to 55 (favorable range, p=0.003, +0.29% EV improvement)
  2. Time: Before 10:30 AM (8% higher win rate, p=0.01)
  3. Exclude Fridays (negative EV day, -0.12% vs +0.52%)

PARAMETERS:
  Stop Loss: 6% (optimal per sensitivity sweep, reduces max DD by 12%)
  Efficiency: 5% (unchanged)
  Fractional Kelly: 20% (reduced from 25% for additional safety margin)

EXPECTED PERFORMANCE (vs baseline):
  Trades: 8,241 → 4,892 (-40.6% — fewer but higher quality)
  Win Rate: 61.3% → 67.8% (+6.5pp)
  EV: 0.42% → 0.71% (+69%)
  Kelly: 18.7% → 28.4% (+52%)
  Max DD: -14.2% → -8.7% (-39%)
  Sharpe: 1.24 → 1.89 (+52%)

MONTE CARLO VALIDATION:
  Probability of ruin (50% DD): 4.2% → 0.8%
  5th percentile final equity: $87,400 → $124,200

CONFIDENCE: MODERATE-HIGH
  ✓ Feature ranges statistically significant (p < 0.01)
  ✓ Monte Carlo validates robustness
  ⚠ Trade count reduction of 40% may increase variance
  ⚠ RSI filter may not persist in different market regimes
```

### 8.4 Additional AI Capabilities

| Capability | Description | Engines Used |
|-----------|-------------|-------------|
| **Daily Briefing** | Auto-generate end-of-day strategy summary | All |
| **What-If Analysis** | "What happens if I change stop loss to 5%?" | ParameterSensitivity + LLM |
| **Risk Narrator** | Plain-English risk assessment | MonteCarlo + LLM |
| **Feature Detective** | Deep-dive into why a feature matters | FeatureAnalyzer + LLM |
| **Drawdown Advisor** | Guidance during drawdown periods | Equity + MonteCarlo + LLM |
| **Comparison Reporter** | Compare two filter sets with narrative | MetricsCalc × 2 + LLM |
| **Data Quality Audit** | Check for data issues, gaps, outliers | DataFrame analysis + LLM |

---

## 9. Implementation Roadmap

### Phase 1: MCP Server (Foundation)

**Goal:** Claude Desktop can query Lumen data interactively via subscription.

**New files:**
```
src/mcp/
├── __init__.py
├── server.py           # MCP server entry point
├── tools/
│   ├── __init__.py
│   ├── data_tools.py   # load_data, get_summary, filter_data
│   ├── metrics_tools.py # get_metrics, compare_metrics
│   ├── analysis_tools.py # analyze_features, run_monte_carlo
│   ├── anomaly_tools.py  # scan_anomalies, detect_regime_change
│   └── strategy_tools.py # suggest_strategy, optimize_params
├── resources.py        # MCP resource definitions
└── prompts.py          # Reusable prompt templates
```

**Dependencies:**
```toml
[project.optional-dependencies]
mcp = [
    "mcp>=1.0.0",
]
```

### Phase 2: LangChain + Ollama Integration

**Goal:** Automated analysis pipelines embedded in Lumen UI.

**New files:**
```
src/ai/
├── __init__.py
├── orchestrator.py     # Main analysis coordinator
├── agents/
│   ├── __init__.py
│   ├── trend_agent.py  # Trend detection
│   ├── anomaly_agent.py # Anomaly detection
│   └── strategy_agent.py # Strategy generation
├── providers/
│   ├── __init__.py
│   ├── ollama_provider.py  # Ollama (free)
│   └── claude_provider.py  # Claude API (optional)
└── prompts/
    ├── __init__.py
    └── trading_prompts.py  # All system prompts
```

**New UI tab:**
```
src/tabs/
└── ai_insights_tab.py  # New tab for AI analysis results
```

### Phase 3: Strategy Advisor

**Goal:** Full strategy generation pipeline with validation.

**Extends Phase 2 with:**
- Multi-step strategy generation (feature → filter → validate → report)
- Strategy comparison and backtesting integration
- Export strategy reports as formatted documents

### Phase 4: Portfolio AI (Advanced)

**Goal:** AI-powered portfolio construction and rebalancing.

- Cross-strategy correlation analysis with narrative
- Automated portfolio weight optimization
- Regime-aware strategy selection

---

## 10. Appendix: Cost Comparison

### Monthly Cost Estimates

| Approach | Setup Cost | Monthly Cost | Quality (1-10) | Automation |
|----------|-----------|-------------|----------------|------------|
| MCP + Claude Pro | $0 | $20 (subscription) | 9 | Interactive |
| MCP + Claude Max | $0 | $100 (subscription) | 10 | Interactive |
| Ollama (local) | $0-2000 (GPU) | $0 | 6-7 | Full |
| Claude API (Haiku) | $0 | $1-10 | 7 | Full |
| Claude API (Sonnet) | $0 | $5-50 | 9 | Full |
| Claude API (Opus) | $0 | $10-200 | 10 | Full |
| Hybrid: MCP + Ollama | $0-2000 (GPU) | $20 (subscription) | 9 interactive, 7 auto | Both |

### Recommended Path

**Start with:** MCP Server (Phase 1) — immediate value with existing subscription.

**Add later:** Ollama integration (Phase 2) — when you want automated daily reports
and in-app AI insights without additional subscription costs.

**Consider:** Claude API (Phase 3/4) — only if Ollama quality is insufficient for
strategy generation, and you need Claude-quality automated pipelines. Even then, Haiku
at $1-10/month is negligible cost.

---

## Appendix: Key Lumen Files Reference

| File | Purpose | Lines |
|------|---------|-------|
| `src/core/metrics.py` | 25 trading metrics | 510 |
| `src/core/statistics.py` | 7 analytical tables | 1,461 |
| `src/core/feature_analyzer.py` | Feature importance ranking | 949 |
| `src/core/monte_carlo.py` | Monte Carlo simulation | 601 |
| `src/core/parameter_sensitivity.py` | Parameter sweep | 869 |
| `src/core/equity.py` | Equity curve calculation | 430 |
| `src/core/portfolio_metrics_calculator.py` | Portfolio analysis | 960 |
| `src/core/app_state.py` | Signal-driven state management | 143 |
| `src/core/models.py` | Data models (TradingMetrics, etc.) | 518 |
| `src/core/file_loader.py` | File import (CSV/Excel/Parquet) | ~200 |
