# Источники исследования display.tool_progress (11.07.2026)

## Reddit
- r/hermesagent, пост "[ask]hide tools call"
- URL: https://www.reddit.com/r/hermesagent/comments/1u304bx/askhide_tools_call

## GitHub Issues
- Issue #34653: config show omits display.* keys
- URL: https://github.com/NousResearch/hermes-agent/issues/34653
- Issue #6164: per-platform tool_progress overrides
- URL: https://github.com/NousResearch/hermes-agent/issues/6164

## Документация
- Mintlify reference: display.tool_progress: "all" # off | new | all | verbose
- URL: https://nousresearch-hermes-agent.mintlify.app/reference/configuration-options

## Команда
```bash
hermes config set display.tool_progress off
hermes config set display.show_reasoning false
```

## Значения
| off | new | all | verbose |
|-----|-----|-----|---------|
| не показывать | только новые | все (умолч.) | подробно |
