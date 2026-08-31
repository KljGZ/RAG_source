# Prompt policy

Development prompts may change only on development data. Before a confirmatory run,
copy reviewed prompts to `frozen/`, generate SHA-256 entries in `MANIFEST.json`, and
tag the commit. Prompt changes after a run create a new experiment version; they do
not overwrite prior logs.

Prompts request concise structured factors, never hidden chain-of-thought.
