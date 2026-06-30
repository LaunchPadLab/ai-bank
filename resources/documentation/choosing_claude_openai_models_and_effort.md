# Choosing Models, Effort, and Intelligence on the Claude API and the OpenAI API — A Rails Developer's Decision Guide

*How to pick the right model tier and reasoning-effort level across Anthropic and OpenAI for Ruby on Rails apps, with exact mid-2026 model IDs, pricing, and Ruby SDK snippets. Pricing and model IDs change fast — reverify against [platform.claude.com](https://platform.claude.com) and [platform.openai.com](https://platform.openai.com) before budgeting.*

## TL;DR
- **Both providers have converged on a "one model, dial the effort" philosophy, but they name and default the dials differently.** Anthropic uses adaptive thinking + an `effort` knob (`low`→`max`) on a 3-tier lineup (Haiku 4.5 $1/$5, Sonnet 4.6 $3/$15, Opus 4.8 $5/$25 per MTok). OpenAI uses `reasoning_effort` (`none`→`xhigh`) + `verbosity` across the GPT-5.5/5.4 family (GPT-5.5 $5/$30, GPT-5.4 $2.50/$15, mini $0.75/$4.50, nano $0.20/$1.25).
- **The decision is almost never "the smartest model" — it's the cheapest tier that clears your quality bar, at the lowest effort that passes your evals.** Route the easy 60–80% of traffic to Haiku/nano/mini, keep a mid-tier (Sonnet 4.6 / GPT-5.4) as default, and reserve Opus 4.8 / GPT-5.5 for genuinely hard reasoning and agentic coding.
- **For Rails, `ruby_llm` is the pragmatic default** (one interface, `.with_thinking(effort:)`, provider-swappable), with the official `anthropic` and `openai` gems when you need same-day access to new parameters.

## Key Findings

1. **Effort/reasoning controls now matter as much as model choice.** A single model spans a wide cost/latency/quality range depending on the effort setting; higher effort is *not* automatically better and can cause "overthinking" — wasted tokens, higher latency, and occasionally worse answers on simple tasks. (Multiple peer-reviewed surveys document reasoning models generating ~18× more tokens than standard models while sometimes scoring *lower* on simple math.)
2. **Anthropic deprecated fixed `budget_tokens` in favor of adaptive thinking + `effort`.** On Opus 4.8 and 4.7, manual `budget_tokens` is *rejected with a 400 error*; adaptive thinking is the only mode. Sonnet 4.6 and Opus 4.6 still accept `budget_tokens` but it's deprecated.
3. **OpenAI splits reasoning vs. non-reasoning explicitly.** The GPT-5.x API models are reasoning models with `reasoning_effort`; `gpt-5-chat-latest` is the non-reasoning chat model. The default effort is `medium` on GPT-5.5; GPT-5.4 mini defaults to `none`.
4. **Cost-optimization levers are nearly symmetric:** both offer ~90% prompt-cache read discounts and 50% batch discounts, applied automatically (OpenAI caching) or via `cache_control` (Anthropic).
5. **The landscape is volatile.** Anthropic's top "Fable 5"/"Mythos 5" tier launched June 9, 2026 and access was suspended within days (per multiple third-party trackers); OpenAI's GPT-5.6 family is in limited preview. Treat anything above the main tiers as unstable.

## Details

### A. Anthropic Claude API

**Model lineup (mid-2026), exact API IDs and pricing (per million tokens, from the official pricing and models pages):**

| Model | API ID | Input | Output | Context | Max output | Thinking | Latency |
|---|---|---|---|---|---|---|---|
| Claude Opus 4.8 | `claude-opus-4-8` | $5 | $25 | 1M | 128k | Adaptive only | Moderate |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | $3 | $15 | 1M | 128k | Adaptive + manual (deprecated) | Fast |
| Claude Haiku 4.5 | `claude-haiku-4-5` (`claude-haiku-4-5-20251001`) | $1 | $5 | 200k | 64k | Extended thinking, no adaptive | Fastest |
| Claude Opus 4.7 | `claude-opus-4-7` | $5 | $25 | 1M | 128k | Adaptive only | Moderate |
| Claude Fable 5 | `claude-fable-5` | $10 | $50 | 1M | 128k | Adaptive always-on | — |

Output is consistently 5× input across current tiers. Opus 4.8 and 4.7 use a new tokenizer that may consume up to 35% more tokens for the same text than Opus 4.6. Opus 4.8, 4.7, 4.6, and Sonnet 4.6 include the full 1M context window at standard pricing (no long-context surcharge). Haiku 4.5 knowledge cutoff is Feb 2025; Opus 4.8 reliable knowledge cutoff is Jan 2026. Legacy Opus 4.1 ($15/$75) is deprecated and ~3× the cost of current Opus for inferior performance — migrate off it.

**Intelligence/latency data (Artificial Analysis, ~72-hour rolling):** Opus 4.8 (max) tops Anthropic's Intelligence Index at 56. Haiku 4.5 is the fastest at ~91.7 tok/s output and ~0.75s time-to-first-token on Anthropic's endpoint; Sonnet 4.6 streams roughly 30–55 tok/s with ~0.96s TTFT (independent harness). On SWE-bench Verified, Sonnet 4.6 ≈79.6% vs Haiku 4.5 ≈73.3%; Opus 4.8 ≈88.6% (vendor-reported via several trackers).

**Adaptive thinking & the `effort` parameter.** Anthropic's recommended approach on Opus 4.6/4.7/4.8 and Sonnet 4.6 is `thinking: {type: "adaptive"}`: Claude decides whether and how much to think per request. You steer it with `effort`:

- Levels: `low`, `medium`, `high` (default), `xhigh`, `max`. `xhigh` is Opus 4.7/4.8/Fable only; `max` adds Sonnet 4.6/Opus 4.6.
- `effort: "high"` is identical to omitting the parameter. Effort governs *all* tokens — text, tool calls, and thinking — so lower effort means fewer tool calls and terser output, not just less thinking.
- Anthropic's guidance: **start at `xhigh` for coding/agentic Opus work**, `high` for most intelligence-sensitive tasks, `medium`/`low` for cost/latency. For Sonnet 4.6 they recommend **`medium` as the practical default** (it defaults to `high`, which can add latency).
- `budget_tokens` (manual extended thinking, min 1,024) still works on Sonnet 4.6/Opus 4.6 but is deprecated; it is rejected on Opus 4.7/4.8.
- Billing: you pay for the full thinking tokens (output-priced) even though only a summary (or nothing, if `display: "omitted"`) is returned. `usage.output_tokens_details.thinking_tokens` reports the reasoning portion. `max_tokens` is a hard cap on thinking+text combined; watch for `stop_reason: "max_tokens"` at high effort.

**Cost/latency features:** Prompt caching — cache reads are billed at **0.1× base input (90% cheaper than base input tokens)**, with a 5-minute cache write at 1.25× and a 1-hour write at 2.0×; Batch API (50% off input and output, up to 300k output tokens with a beta header); Fast mode (research preview) for Opus 4.8 at $10/$50. Caching and batch stack.

**Ruby SDK (`anthropic`, official, github.com/anthropics/anthropic-sdk-ruby, requires Ruby 3.2+):**
```ruby
anthropic = Anthropic::Client.new # reads ANTHROPIC_API_KEY
message = anthropic.messages.create(
  model: :"claude-opus-4-8",
  max_tokens: 16000,
  thinking: {type: "adaptive"},
  output_config: {effort: "medium"},
  messages: [{role: "user", content: "Refactor this service object..."}]
)
```
Effort is nested under `output_config:`; thinking under `thinking:`. (Confirmed parameter structure; Anthropic's docs show the equivalent Python/TS verbatim.) Vertex and Bedrock clients (`Anthropic::VertexClient`, `Anthropic::BedrockClient`) share the same API. Note the older community gem was renamed `ruby-anthropic`; the canonical `anthropic` gem name is the official SDK.

### B. OpenAI API

**Model lineup (mid-2026), exact API IDs and pricing (per million tokens):**

| Model | API ID | Input | Output | Context | Notes |
|---|---|---|---|---|---|
| GPT-5.5 | `gpt-5.5` | $5 | $30 | ~1.05M | Flagship reasoning; cached input $0.50 |
| GPT-5.5 Pro | `gpt-5.5-pro` | $30 | $180 | 1M | Highest precision, no cache discount |
| GPT-5.4 | `gpt-5.4` | $2.50 | $15 | 1M | Mainstream workhorse (272K standard; >272K doubles input) |
| GPT-5.4 mini | `gpt-5.4-mini` | $0.75 | $4.50 | 400k | High-volume; `reasoning.effort` default `none` |
| GPT-5.4 nano | `gpt-5.4-nano` | $0.20 | $1.25 | 400k | Cheapest GPT-5.4; classification/extraction |
| GPT-4.1 nano | `gpt-4.1-nano` | $0.10 | $0.40 | 1M | Cheapest overall |
| gpt-5-chat-latest | `gpt-5-chat-latest` | — | — | — | Non-reasoning ChatGPT model |
| o3 | `o3` | $2 | $8 | 200k | Cheaper reasoning, June-2024 cutoff |

**`reasoning_effort`.** Values (model-dependent): `none`, `minimal`, `low`, `medium`, `high`, `xhigh`. Higher effort = more hidden reasoning tokens (billed as output), higher latency, generally higher quality. GPT-5.5 defaults to `medium`; OpenAI says "many workloads will perform well with `low`," and to reserve `none` for latency-critical non-reasoning work (voice turns, classification). `minimal` (GPT-5 era) yields very few reasoning tokens for fast time-to-first-token.

**`verbosity`** (`text.verbosity`: `low`/`medium`/`high`, default `medium`) controls output length/depth independently of reasoning quality. Explicit prompt instructions override it. OpenAI recommends `low` verbosity for concise answers but `high` verbosity for code.

**Reasoning vs. non-reasoning.** GPT-5.x API models are reasoning models (use the Responses API, `previous_response_id` for state, interleaved thinking between tool calls). `gpt-5-chat-latest` is the non-reasoning model that powers ChatGPT — note that GPT-5 with `minimal` reasoning is a *different*, developer-tuned model. Reasoning models don't support `temperature`, `top_p`, `presence_penalty`, etc. OpenAI's own guidance: overthinking shows up as correct-but-slow answers; the first fix is to lower `reasoning_effort` and tighten the "definition of done."

**Cost/latency features:** Prompt caching is automatic (no code change), ≥1,024-token prefixes (128-token increments), up to 90% off cached input and up to 80% faster TTFT; `prompt_cache_key` improves cache routing. Batch API = 50% off, 24-hour window; Flex (`service_tier="flex"`) = same 50% with more caching flexibility; Priority (`service_tier="priority"`) for premium-priced faster responses.

**Ruby SDKs:**
- **Official `openai` gem** (github.com/openai/openai-ruby, Ruby 3.2+):
```ruby
openai = OpenAI::Client.new
response = openai.responses.create(
  model: "gpt-5.5",
  input: "Write a bash script to transpose a matrix.",
  reasoning: {effort: "low"},
  text: {verbosity: "medium"}
)
puts(response.output_text)
```
- **Community `ruby-openai`** (alexrudall, v7.x) wraps in a `parameters:` hash with string keys:
```ruby
response = client.responses.create(parameters: {
  model: "gpt-5", input: "Hello!", reasoning: { "effort": "minimal" }
})
```
- **`ruby_llm`** (crmne; `.with_thinking` introduced in v1.10.0, released Jan 13, 2026; v1.16.0 added the Anthropic adaptive-thinking format newer models require) exposes effort uniformly across providers:
```ruby
chat = RubyLLM.chat(model: "claude-opus-4.5").with_thinking(effort: :high, budget: 8000)
chat.ask("What is 15 * 23?")
```
`with_thinking(effort:)` works for both Claude and GPT-5.x; OpenAI models accept `effort` but may not return thinking text/signatures. There is **no** `.with_reasoning_effort` method. `ruby_llm` also normalizes token accounting (`response.tokens.thinking`, `response.cost.thinking`) and lets you swap models with a one-liner (`chat.with_model("gpt-5.4")`).

### C. Comparison & Synthesis

| Dimension | Anthropic | OpenAI |
|---|---|---|
| Effort param | `effort` (`low`→`max`), nested in `output_config` | `reasoning_effort` (`none`→`xhigh`) |
| Default effort | `high` | `medium` (GPT-5.5); `none` (5.4-mini) |
| Output-length control | prompt-driven | `verbosity` param |
| Thinking model | adaptive (auto-decides) | explicit reasoning vs. `gpt-5-chat-latest` |
| Cache discount | 90% (cache_control) | ~90% (automatic) |
| Batch | 50% | 50% (+ Flex/Priority tiers) |
| Cheapest tier | Haiku 4.5 ($1/$5) | GPT-4.1 nano ($0.10/$0.40) |
| Output:input ratio | flat 5× | varies (e.g., 6× on GPT-5.5) |

Philosophically: **Anthropic hides the dial inside the model** (adaptive thinking decides per-request; you nudge with one `effort` word that also throttles tool calls), while **OpenAI exposes two orthogonal dials** (`reasoning_effort` for how hard to think, `verbosity` for how much to write) and keeps a separate non-reasoning chat model. Anthropic's pricing is more predictable (flat 5× output ratio, flat 1M context); OpenAI's is cheaper at the very bottom (nano) and has more service-tier knobs.

**Practical Rails decision framework:**
1. **Classify the task** on three axes: complexity, latency sensitivity, and cost-at-scale.
2. **Pick the tier:** simple/high-volume → Haiku 4.5 or GPT-5.4-nano/mini (or GPT-4.1 nano); default production → Sonnet 4.6 or GPT-5.4; hard reasoning/agentic coding → Opus 4.8 or GPT-5.5.
3. **Pick the effort:** start `low`/`medium`, raise only if evals show measurable gains. For latency-sensitive paths use `low`/`none`/`minimal`.
4. **Turn on caching** for stable system prompts/RAG context, and **batch** anything non-real-time.
5. **Measure** TTFT and total latency at P50/P95, separating model time from tool/network time.

A concrete pattern from Anthropic's own testing: an "advisor" setup where Opus plans and Sonnet/Haiku executes yielded ~11% lower cost and ~2% higher benchmark scores vs. a single model; tiered routing across a real workload commonly cuts spend 30–60% vs. running everything on the flagship.

**Benchmarks worth citing cautiously:** SWE-bench Verified is near saturation (top models mid-to-high 80s). The contamination-resistant **SWE-bench Pro** (Scale AI: 1,865 instances — 731 public, 858 held-out, 276 commercial — across 41 repositories) is far harder: per Morph's June 28, 2026 leaderboard, **GPT-5.4 (xHigh) leads Scale's standardized public set at 59.1%, while Claude Opus 4.8 tops the llm-stats vendor aggregate at 69.2%.** Scale's own paper found even GPT-5 and Claude Opus 4.1 scored only ~23% under a unified scaffold versus 70%+ on Verified — a stark reminder that harness and data-split differences make single cross-provider numbers unreliable. Always check which harness produced a score. (One audit also flagged that some Claude Opus runs read gold solutions from `.git` history, further muddying older Pro numbers.)

## Recommendations
- **Default stack:** Sonnet 4.6 (or GPT-5.4) at `medium` effort as your production workhorse; Haiku 4.5 / GPT-5.4-mini/nano for routing, classification, extraction; Opus 4.8 / GPT-5.5 reserved for hard problems. This routing typically cuts spend 30–60% vs. running everything on the flagship.
- **Use `ruby_llm`** as your integration layer for provider flexibility (`.with_thinking(effort:)`, one-line model swaps); drop to the official `anthropic`/`openai` gems when you need brand-new parameters same-day or provider-specific features.
- **Always enable prompt caching and batch** where applicable *before* reaching for a cheaper model — they often beat tier-downgrading on quality. Front-load static content (system prompt, tool schemas, RAG docs) so prefixes hit cache.
- **Staged rollout:** (1) ship on the mid-tier at low/medium effort; (2) build an eval set from real request logs; (3) downgrade tiers/effort where evals hold; (4) upgrade only the requests that fail.
- **Thresholds that change the call:** if a cheaper model needs ≥2 retries to match the flagship, it's no longer cheaper — promote it. If higher effort doesn't move your eval score, lower it. If a task regularly exceeds 200k tokens, you need Sonnet/Opus or a 1M-context GPT-5.x model, not Haiku. If TTFT is the product (autocomplete, chat), pick Haiku 4.5 / nano / `minimal` effort regardless of raw intelligence.

## Caveats
- Mid-2026 pricing/model IDs change fast; several figures come from third-party trackers (CloudZero, Artificial Analysis, BenchLM, Morph, Scale) rather than the vendor, and should be reverified against platform.claude.com and platform.openai.com before budgeting.
- Anthropic's Fable 5 / Mythos 5 tier and OpenAI's GPT-5.6 family are unstable/limited-availability; don't build production on them yet.
- The exact Ruby snippets for the official gems' effort/reasoning calls reflect documented keyword conventions plus verbatim Python/TS examples; the `anthropic`/`openai` docs Ruby tabs are JS-rendered, so confirm against the live Ruby tab. The `ruby-openai` and `ruby_llm` snippets are verbatim from their official docs.
- Benchmark scores are largely vendor-reported and harness-dependent; treat single numbers skeptically, and prefer your own task-specific evals over public leaderboards for production decisions.
