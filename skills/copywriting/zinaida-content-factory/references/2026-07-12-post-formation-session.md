# Session 12.07.2026 — Writer formation & infrastructure

## Key decisions

1. 2 deep research + 1 quality control per post, not 3 deep research
   - Research #1: 4 agents in internet — scientific base, statistics, neurobiology
   - Research #2: 4 agents on server — phases.db, smm_rag.db, stats, templates
   - Quality control: post_analyzer.py — AI-patterns, blacklist, punctuation

2. Instruments are FREE entry into the product, not a monetization channel
   - Writer NEVER writes about prices or tokens
   - Funnel: post -> keyword in comments -> free instrument access -> see Zinaida's power -> subscription

3. 6 banned patterns forever (see 14_WRITER_FORMATION.md)

4. Oleg's core demand: I must DO work when I say "начинаю", not pretend. He catches fake activity.

## Scripts created/modified

- /opt/zinaida/scripts/server_research.py — NEW: 4 agents searching server databases
- /opt/zinaida/scripts/write_post_orchestrator.py — NEW: 11-step orchestrator
- Backups in *.bak_20260712

## Document created

/opt/zinaida/projects/Otnoshenya/pisatel/14_WRITER_FORMATION.md — complete writer system
