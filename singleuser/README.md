# Single-user runtime defaults

Mounted read-only at `/opt/lab-meteo` in every user container (host path `LAB_SINGLEUSER_CONFIG_HOST`).
At start-up the server copies `user-settings/` into `~/.jupyter/lab/user-settings/` without
overwriting existing files, so these are defaults that users can change from *Settings*.

They make JupyterLab and Notebook 7 behave like Google Colaboratory:

| Setting | Colab behaviour |
|---|---|
| `Ctrl+M` then `B`/`A`/`D`/`M`/`Y`/`I`/`.`/`Z`/`-`/`K`/`J` | insert below/above, delete, Markdown, code, interrupt, restart, undo, split, move up/down |
| `Ctrl+F9`, `Ctrl+F8`, `Ctrl+F10` | run all, run before, run after |
| `autoCompletion` | suggestions while typing |
| `autoClosingBrackets` | brackets and quotes close automatically |
| `recordTiming` | execution start and end times stored per cell |
| `autosaveInterval: 30` | frequent autosave |
| `fetchNews: "false"`, `checkForUpdates: false` | no prompts and no requests to jupyter.org for news or updates |
