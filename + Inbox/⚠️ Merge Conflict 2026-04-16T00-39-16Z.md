---
title: Merge Conflict 2026-04-16T00-39-16Z
created: 2026-04-16T00-39-16Z
tags: [needs-review, openbrain-error]
---

# Merge Conflict — 2026-04-16T00-39-16Z

The Stop hook tried to `git pull --rebase` and hit conflicts. The rebase was aborted; your local changes are intact but **not committed or pushed**.

## To resolve

1. Open a terminal in `/Users/brichards/repos/openbrain`
2. Run `git status` to see what diverged
3. Manually merge / rebase and push
4. Delete this note when done

## Log tail

```
[33m⚠ pre-commit: .claude/skills/daily-brief/SKILL.md: broken wikilink [[wikilinks]][0m
[33m2 warning(s) — commit proceeding anyway (warn-only mode)[0m
[main 4811133] auto: vault update (1 file changed, 4 insertions(+), 1 deletion(-))
 1 file changed, 4 insertions(+), 1 deletion(-)
To github.com:brady-richards/openbrain.git
   c61f314..4811133  main -> main
Already up to date.
[33m⚠ pre-commit: .claude/skills/daily-brief/SKILL.md: frontmatter missing 'title' or 'date'[0m
[33m⚠ pre-commit: .claude/skills/daily-brief/SKILL.md: broken wikilink [[wikilinks]][0m
[33m2 warning(s) — commit proceeding anyway (warn-only mode)[0m
[main 5de8e4d] auto: vault update (1 file changed, 4 insertions(+), 3 deletions(-))
 1 file changed, 4 insertions(+), 3 deletions(-)
To github.com:brady-richards/openbrain.git
   4811133..5de8e4d  main -> main
sign_and_send_pubkey: signing failed for ED25519 "/Users/brichards/.ssh/id_ed25519" from agent: communication with agent failed
Connection closed by 140.82.114.4 port 22
fatal: Could not read from remote repository.

Please make sure you have the correct access rights
and the repository exists.
```
