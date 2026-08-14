# Hermes clean Gemini rebuild

The legacy Hermes copy is retained for reference. The clean runtime path installs the upstream Hermes Agent release with its native Gemini provider.

- Hermes Agent: `0.18.2`
- Provider: `gemini`
- Model: `gemini-3.6-flash`
- Secret: `GEMINI_API_KEY` from the GitHub Codespaces environment
- No OpenRouter dependency for the primary model

The rebuild script preserves old `~/.hermes` state as a timestamped legacy backup, installs the pinned upstream release, writes only non-secret model configuration, verifies direct Gemini access, and then runs a one-shot Hermes → Gemini smoke test. The API key is never written to the repository or printed.
