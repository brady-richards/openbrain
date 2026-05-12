---
title: Merge Conflict 2026-05-12T11-52-26Z
created: 2026-05-12T11-52-26Z
tags: [needs-review, openbrain-error]
---

# Merge Conflict — 2026-05-12T11-52-26Z

The Stop hook tried to `git pull --rebase` and hit conflicts. The rebase was aborted; your local changes are intact but **not committed or pushed**.

## To resolve

1. Open a terminal in `/Users/brichards/repos/openbrain`
2. Run `git status` to see what diverged
3. Manually merge / rebase and push
4. Delete this note when done

## Log tail

```
 create mode 100644 asana.csv
 create mode 100644 data/.gemini/asana.csv
 create mode 100644 data/.gemini/skills/brief-me/scripts/analyze_data.py
 create mode 100644 data/asana.csv
 create mode 100644 data/orientation.md
 create mode 100644 mcp_config.json
 create mode 100644 mcp_servers_extract.json
To github.com:brady-richards/openbrain.git
   7563df5..f655b53  main -> main
Already up to date.
[main 1f6ed72] auto: vault update (1 file changed, 0 insertions(+), 0 deletions(-))
 1 file changed, 0 insertions(+), 0 deletions(-)
To github.com:brady-richards/openbrain.git
   f655b53..1f6ed72  main -> main
sign_and_send_pubkey: signing failed for ED25519 "/Users/brichards/.ssh/id_ed25519" from agent: communication with agent failed
git@github.com: Permission denied (publickey).
fatal: Could not read from remote repository.

Please make sure you have the correct access rights
and the repository exists.
```
