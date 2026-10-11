# Codex Cloud setup

Connect this GitHub repository to your Codex cloud environment and select its
`main` branch. Give the GitHub connection access to the repository if it is private.
Use Python 3.12 or newer and set the environment setup command to:

```bash
bash scripts/setup_codex_cloud.sh
```

The script installs locked core dependencies, runs the regression suite, and runs
the bundled offline refresh sample. It does not download company datasets or
install optional browser and sentiment dependencies. `AGENTS.md` supplies project
context and commands automatically; a separate skill is not needed for this setup.

For a first task, ask:

> Read AGENTS.md and HANDOFF.md, run the offline checks, and report the current
> project state without changing application code.

Live company research needs agent internet access and the downloads documented in
README. The existing local `out/` runs, caches, and bulk datasets are not in Git;
references to those artifacts in the handoff are historical. A fresh cloud
checkout can run the bundled fixtures but cannot inspect those old local runs.

Official guidance:
- https://developers.openai.com/codex/cloud/environments
- https://developers.openai.com/codex/guides/agents-md
