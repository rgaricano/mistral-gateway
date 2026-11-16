---
type: Configuration Bundle
title: Gentle Shell configuration for the Mistral gateway
version: "1.0.0"
description: pi settings.json and models.json extracted from a working gentle-shell installation, reduced to the Mistral providers, for reuse in new or existing installations.
tags: [pi, gentle-shell, mistral-gateway, configuration, openai-completions]
status: stable
generated: { by: el_gentleman/gentle-pi, at: 2026-11-16T04:49:00Z }
verified: { by: human:rgaricano, at: 2026-11-16T04:49:00Z }
sources:
  - id: gentle-shell-live
    resource: /home/ricardo/.gentle-shell/agent
    title: Live gentle-shell agent configuration
    author: human:rgaricano
    last_modified: 2026-11-16T04:49:00Z
  - id: gateway-readme
    resource: ../README.md
    title: mistral-gateway documentation
    author: human:Classic298
---

# Gentle Shell models configuration

Versión en español: [README.es.md](./README.es.md).

Snapshot of a working pi/gentle-shell configuration that talks to the local
[mistral-gateway](../README.md), reduced to the Mistral providers.

## What each file is

| File | Target path | Purpose |
|------|-------------|---------|
| `models.json` | `~/.gentle-shell/agent/models.json` | Declares the `Mistral-local` provider: base URL, API type, 16 chat models with real capabilities (reasoning levels, context window, input modalities, cost). |
| `settings.json` | `~/.gentle-shell/agent/settings.json` | Runtime settings: default model, enabled models, per-model compaction thresholds. |

Both files come from `~/.gentle-shell/agent/` on the machine where the gateway
was configured, taken after the full setup was verified end-to-end (reasoning,
tool calls, both Mistral providers).

## What they configure

- **Provider** `Mistral-local`: OpenAI-compatible relay at `http://127.0.0.1:8788/v1`
  (this gateway), using the `openai-completions` API. 16 chat models, aliases
  collapsed (`zai-glm-5` -> `zai-glm-5-3`, etc.).
- **Defaults**: `Mistral-local` / `zai-glm-5-3-flash`, thinking level `medium`.
- **Enabled models**: 28 (16 from the gateway + 12 from pi's built-in `mistral`
  provider, which points at Mistral's public API and needs its own credentials
  in `auth.json`).
- **Compaction**: enabled, with per-model overrides — models with a context
  window >= 500K tokens compact at 60% usage, smaller ones at 80%.

## Reasoning levels

The `thinkingLevelMap` in `models.json` only offers the levels each model
really accepts. This is deliberate: the gateway's Vibe-Code channel maps an
unsupported level to the closest supported one silently, so offering levels a
model cannot honour would make pi show choices that do not do what they say
(a `medium` that is really `high`, spending Vibe budget accordingly).

| Model | Levels offered |
|-------|----------------|
| `deepseek-v4-1-flash-1017` | off, low, high, xhigh, max |
| `zai-glm-5-3`, `zai-glm-5-3-flash`, `glm-5.2` | low, high, max |
| `mistral-large`, `mistral-large-4`, `mistral-medium-latest`, `mistral-small-2603`, `magistral-medium-latest`, `labs-leanstral-1-5-1`, `mistral-vibe-cli-with-tools` | off, high |
| `codestral-2508`, `ministral-*`, `voxtral-small-2507` | no reasoning |

Notes:

- Vibe-Code only grants each model a subset of the standard levels, which is
  why the map is narrower than pi's full set. The gateway maps anything else
  to the nearest supported level (down for `minimal`/`low`, up for the rest).
- `off` maps to the gateway's `none`. The `zai-glm-*` models cannot turn
  reasoning off, only lower it to `low`.
- Levels hidden with `null` are not sent at all; pi clamps the selection to
  the nearest supported one instead of letting the gateway decide silently.

## Compaction criteria

Compaction summarises the conversation when it grows too large. The
thresholds here follow two recommended practices for keeping model responses
good:

- **Large windows (>= 500K tokens) compact at 60% usage** (reserve 419430 of
  1048576). A huge transcript degrades the model's focus long before it fills
  the window, so summarising earlier keeps answers sharp; and summarising that
  much content is expensive, so it should not happen constantly.
- **Smaller windows compact at 80% usage** (reserve ~52428 of 262144). There
  is less room, but the transcript is also cheaper to summarise, so it can
  wait a little longer.
- **Small models (`ministral-*`, `voxtral-small-2507`, reserve 0) do not
  compact.** pi has no per-model compaction switch; `reserveTokens: 0` is the
  closest equivalent (the trigger then only fires past the full window, which
  in practice never happens). Their windows are too small for a summary to
  pay off: the summarisation request itself would eat a large share of the
  context the model has.

## Pricing

The `cost` field in `models.json` carries **Mistral's official list prices**
(USD per million tokens), taken from [Mistral's pricing page](https://docs.mistral.ai/inference/pricing)
and each model's docs. pi multiplies them by the tokens of each request, which
is what the session statistics show.

| Model | Input $/M | Input €/M | Cached $/M | Cached €/M | Output $/M | Output €/M |
|-------|----------:|----------:|-----------:|-----------:|-----------:|-----------:|
| `magistral-medium-latest` | 2 | 1.84 | 0.15 | 0.138 | 5 | 4.6 |
| `mistral-medium-latest` | 1.5 | 1.38 | 0.15 | 0.138 | 7.5 | 6.9 |
| `zai-glm-5-3` | 1.4 | 1.288 | 0.14 | 0.1288 | 4.4 | 4.048 |
| `glm-5.2` | 1.4 | 1.288 | 0.26 | 0.2392 | 4.4 | 4.048 |
| `mistral-large` | 0.7 | 0.644 | 0.07 | 0.0644 | 2.1 | 1.932 |
| `mistral-large-4` | 0.7 | 0.644 | 0.07 | 0.0644 | 2.1 | 1.932 |
| `deepseek-v4-1-flash-1017` | 0.3 | 0.276 | 0.007 | 0.0064 | 1.2 | 1.104 |
| `codestral-2508` | 0.3 | 0.276 | 0.03 | 0.0276 | 0.9 | 0.828 |
| `ministral-14b-2512` | 0.2 | 0.184 | 0.02 | 0.0184 | 0.2 | 0.184 |
| `zai-glm-5-3-flash` | 0.15 | 0.138 | 0.03 | 0.0276 | 0.5 | 0.46 |
| `mistral-small-2603` | 0.15 | 0.138 | 0.015 | 0.0138 | 0.6 | 0.552 |
| `mistral-vibe-cli-with-tools` | 0.15 | 0.138 | 0.015 | 0.0138 | 0.6 | 0.552 |
| `ministral-8b-2512` | 0.15 | 0.138 | 0.015 | 0.0138 | 0.15 | 0.138 |
| `ministral-3b-2512` | 0.1 | 0.092 | 0.01 | 0.0092 | 0.1 | 0.092 |
| `voxtral-small-2507` | 0.1 | 0.092 | 0.01 | 0.0092 | 0.3 | 0.276 |
| `labs-leanstral-1-5-1` | 0 | 0 | 0 | 0 | 0 | 0 | (free Labs preview)

Rates: 1 USD ≈ 0.92 EUR (reference only; the `cost` values in `models.json` are the USD column). `cacheWrite` is 0 for every model: Mistral does not bill cache writes separately.

**What the numbers are, and are not.** The Vibe plan is a monthly budget, not pay-per-token: the gateway's `/quota` endpoint is the source of truth for real spending. Measured against a real billing export, this configuration's usage billed at ~0.92x list prices, so the statistics are a fair reference for comparing models and estimating cost, slightly above what the plan actually consumes. Two reasons the real number comes in lower: the plan's budget mechanics, and prompt caching — over half of the measured traffic was served from cache at 10-20% of the input rate.

Example from an anonymised 16-day export: ~240M total tokens on `zai-glm-5-3-flash`, of which ~197M (82%) were cached reads. At list prices that usage is ~$9.76; the cache discount is what keeps the effective rate down, not a per-token discount on the plan.

## Which subscription each provider uses

The two providers in `models.json` reach Mistral through different channels:

- **`Mistral-local`** goes through this gateway. It uses the **Mistral Pro
  subscription** via the Vibe key: the gateway sends requests with
  **Vibe-Code precedence** (the Vibe plan budget is consumed first) and falls
  back to the **Studio API key** when the Vibe key is rate limited or its
  monthly budget is spent. Credential handling lives entirely in the gateway
  (`gateway.env`); gentle-shell never sees a key for this provider.
- **`mistral`** (gentle-shell's built-in provider) talks to Mistral's public API
  directly from gentle-shell, with credentials configured in gentle-shell itself
  (`gentle-shell auth login mistral`). It uses the **Pro subscription's API access
  directly**, with **API precedence and no access to Vibe-Code**: what is
  consumed there is billed through the plan's API usage, never through the
  Vibe coding budget.

Both point at the same Pro plan, but through different doors: what each one
spends depends on which channel the request took.

## New installation

Prerequisite: the gateway is running locally (see the [main README](../README.md)).

1. Copy the files to their target paths, creating the directory if needed:

   ```bash
   mkdir -p ~/.gentle-shell/agent
   cp models.json settings.json ~/.gentle-shell/agent/
   ```

2. If the public `mistral` provider is wanted, add its credentials:

   ```bash
   gentle-shell auth login mistral
   ```

   Without credentials those 12 `mistral/*` models stay listed but fail on use.

3. Restart gentle-shell so the configuration is loaded.

## Existing installation

Merge instead of overwrite: the target machine may already have other providers
(`Omniroute-local`, `LlamaSwap-local`, ...) that must survive.

1. Back up the current files:

   ```bash
   cp ~/.gentle-shell/agent/models.json ~/.gentle-shell/agent/models.json.bak
   cp ~/.gentle-shell/agent/settings.json ~/.gentle-shell/agent/settings.json.bak
   ```

2. In `models.json`, add the `Mistral-local` provider from this bundle to the
   existing `providers` object. Do not replace the whole file if other
   providers are present.

3. In `settings.json`, merge three sections:
   - `enabledModels`: append the 28 entries from this bundle.
   - `compaction.modelOverrides`: append the per-model thresholds.
   - `defaultProvider` / `defaultModel`: set to `Mistral-local` /
     `zai-glm-5-3-flash` only if the installation should switch over.

4. Restart gentle-shell.

## Caveats

- The gateway must be reachable at `127.0.0.1:8788`; if it listens elsewhere,
  update `baseUrl` in `models.json`.
- `models.json` is the single source of truth for providers: no
  custom-provider extension is needed, and installing one would shadow this
  configuration.
- Reasoning levels are restricted to what each model really accepts (the
  gateway maps unsupported levels silently). `zai-glm-*` models cannot turn
  reasoning off, only lower it.
