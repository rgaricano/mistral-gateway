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
