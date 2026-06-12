# @pwg/agents

LLM agent definitions for the 15 agents in the master spec §6. **Empty in Phase 0** —
populated starting Phase 1 (Trend Scout, Topic Scorer) then onward.

Each agent will be: `run(input, ctx) -> zod-validated output`, logging to `agent_runs` +
`costs`, retrying with exponential backoff (max 3), emitting `system_events` on failure.
Prompts are versioned files (not inline strings) and each prompt includes: role, input
schema, output JSON schema, 3 few-shot examples, and explicit refuse-to-fabricate rules.

Prompt directory layout (Phase 1+):
```
prompts/
  trend_scout/v1.md
  topic_scorer/v1.md
  ...
```
