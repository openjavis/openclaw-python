---
name: model-usage
description: Track and report model usage and costs
version: 1.0.0
author: ClawdBot
tags: [monitoring, usage, costs]
requires_bins: []
requires_env: []
requires_config: []
---

# Model Usage Tracking

Track LLM usage, token consumption, and estimate costs.

## Monitoring

### Token Usage
Track tokens used in conversations:
- Input tokens
- Output tokens
- Total tokens

### Cost Estimation

#### Anthropic Pricing (as of 2026)
- Claude Opus 4.5: $15 per MTok input, $75 per MTok output
- Claude Sonnet 3.5: $3 per MTok input, $15 per MTok output

#### OpenAI Pricing
- GPT-4 Turbo: $10 per MTok input, $30 per MTok output
- GPT-4: $30 per MTok input, $60 per MTok output

## Usage Examples

User: "How many tokens have I used today?"
1. Query session history
2. Sum token counts
3. Present totals

User: "Estimate my costs for this month"
1. Gather usage statistics
2. Calculate costs per model
3. Present breakdown

User: "Which model is most efficient for my use case?"
1. Compare token usage patterns
2. Calculate cost per conversation
3. Recommend most efficient model

## Best Practices

- Log token usage with each API call
- Store usage data in session metadata
- Provide cost estimates before expensive operations
- Suggest model switching for cost optimization

## Data Structure

```python
usage = {
    "model": "claude-opus-4-5",
    "input_tokens": 1500,
    "output_tokens": 500,
    "cost_usd": 0.06,  # Estimated
    "timestamp": "2026-01-27T00:00:00Z"
}
```

## Reporting

Generate usage reports:
- Daily/weekly/monthly summaries
- Per-model breakdown
- Cost trends
- Token efficiency metrics
