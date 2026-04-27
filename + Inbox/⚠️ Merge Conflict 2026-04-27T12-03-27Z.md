---
title: Merge Conflict 2026-04-27T12-03-27Z
created: 2026-04-27T12-03-27Z
tags: [needs-review, openbrain-error]
---

# Merge Conflict — 2026-04-27T12-03-27Z

The Stop hook tried to `git pull --rebase` and hit conflicts. The rebase was aborted; your local changes are intact but **not committed or pushed**.

## To resolve

1. Open a terminal in `/Users/brichards/repos/openbrain`
2. Run `git status` to see what diverged
3. Manually merge / rebase and push
4. Delete this note when done

## Log tail

```
[33m3 warning(s) — commit proceeding anyway (warn-only mode)[0m
[main 80882ec] auto: 1 atlas (2 files changed, 109 insertions(+), 28 deletions(-))
 2 files changed, 109 insertions(+), 28 deletions(-)
 create mode 100644 + Atlas/Daily/2026-04-24.md
To github.com:brady-richards/openbrain.git
   767a0bc..80882ec  main -> main
Already up to date.
[33m⚠ pre-commit: .claude/skills/daily-brief/SKILL.md: frontmatter missing 'title' or 'date'[0m
[33m⚠ pre-commit: .claude/skills/daily-brief/SKILL.md: broken wikilink [[wikilinks]][0m
[33m2 warning(s) — commit proceeding anyway (warn-only mode)[0m
[main 3c823ae] auto: vault update (1 file changed, 43 insertions(+), 7 deletions(-))
 1 file changed, 43 insertions(+), 7 deletions(-)
To github.com:brady-richards/openbrain.git
   80882ec..3c823ae  main -> main
sign_and_send_pubkey: signing failed for ED25519 "/Users/brichards/.ssh/id_ed25519" from agent: communication with agent failed
git@github.com: Permission denied (publickey).
fatal: Could not read from remote repository.

Please make sure you have the correct access rights
and the repository exists.
```
