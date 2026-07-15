# Post Analyzer Script
Located at: `/opt/zinaida/scripts/post_analyzer.py`

Run before showing any post to Oleg:
```bash
python3 /opt/zinaida/scripts/post_analyzer.py "$(cat /path/to/post.txt)"
```

Checks (16+ items):
- Long dashes (—, –) → fail
- Ellipsis at end → warning
- Pattern "это не X, это Y" → fail
- Filler phrases → fail
- Amplifiers → fail
- Pop-psychology → fail
- Structural traps → fail
- Meta-comments → fail
- Self-reference → fail
- Bureaucratese → fail
- Empty analogies → fail
- Post length → warning
- First line about relationships → pass
- Research citation → warning (verify it's a punch, not proof)
- **NEW (11.07):** Forbidden CTA phrases ("по косточкам", "ни один AI", "это не гадание", "пришлю ссылку") → fail
