# Hermes clean Gemini rebuild

The repository's legacy Hermes copy is kept for reference. The clean runtime path uses the upstream Hermes Agent release with its native Gemini provider.

## Target

- Hermes Agent `0.18.2`
- Provider: `gemini`
- Model: `gemini-3.6-flash`
- Secret: `GEMINI_API_KEY`
- No OpenRouter dependency for the primary model

Run `rebuild-clean-gemini.sh` from the Codespace after confirming `GEMINI_API_KEY` is present in the environment. The script never prints the key value and preserves the previous `~/.hermes` state as a timestamped legacy backup.
