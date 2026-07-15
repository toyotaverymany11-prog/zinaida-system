# Gender Auto-Fix: Post-Processing in Router (11.07.2026)

## Problem
LLM models (DeepSeek, Mistral) statistically default to male grammatical gender in Russian verbs. Even with a strong system prompt rule, the model can "fall back" to male gender during long responses. Олег considers this a CRITICAL error — Зинаида must ALWAYS speak in female gender.

## Solution
Post-processing in the router (`/opt/zinaida/meta_agent/router_8005_v2.py`, step 9 in `_generate()`). The code auto-replaces 32 male verb forms (понял→поняла, сделал→сделала, etc.) in the response before returning it. Logs each fix with `GENDER FIX` tag.

## Three-layer protection
1. System prompt (SOUL.md): 🚨 КРИТИЧЕСКОЕ ПРАВИЛО РОДА
2. Router post-processing: auto-fix male→female verbs
3. Memory rules (Hermes + Mem0)
