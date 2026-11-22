# Contributing

1. Create a focused branch from `main`.
2. Make one coherent change and update its documentation.
3. Run `./scripts/validate_repo.sh` and build affected images.
4. Execute the case study with representative data after scientific changes.
5. Commit with an imperative message and open a pull request.

Follow [AGENTS.md](../AGENTS.md). Pin every direct dependency. Rebuild and exercise the image before
refreshing `scripts/freeze_env.sh` output. Keep notebook prose in Markdown cells, code executable,
and transient output cleared. Full WRF execution is excluded from CI because input is large and
remotely hosted.
