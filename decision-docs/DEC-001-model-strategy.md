# Decision: Live Model and Prompt-Enhancement Model Strategy

## Date
2026-03-08

## Options
- Hardcode model IDs in source
- Use env-var driven model IDs with validated defaults

## Decision
Use env vars:
- `LIVE_MODEL_ID` default: `gemini-2.5-flash-native-audio-preview-12-2025`
- `TEXT_MODEL_ID` default: `gemini-2.5-flash`

## Trade-off
- Slight configuration overhead
- Strong protection against breakage during model deprecations/renames

## Notes
Before every demo/deploy, verify IDs against official Gemini model docs.
