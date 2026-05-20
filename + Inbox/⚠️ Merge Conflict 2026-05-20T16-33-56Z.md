---
title: Merge Conflict 2026-05-20T16-33-56Z
created: 2026-05-20T16-33-56Z
tags: [needs-review, openbrain-error]
---

# Merge Conflict — 2026-05-20T16-33-56Z

The Stop hook tried to `git pull --rebase` and hit conflicts. The rebase was aborted; your local changes are intact but **not committed or pushed**.

## To resolve

1. Open a terminal in `/Users/brichards/repos/openbrain`
2. Run `git status` to see what diverged
3. Manually merge / rebase and push
4. Delete this note when done

## Log tail

```
To github.com:brady-richards/openbrain.git
   7a78073..396895e  main -> main
Already up to date.
[main 2e8a658] auto: vault update (1 file changed, 0 insertions(+), 0 deletions(-))
 1 file changed, 0 insertions(+), 0 deletions(-)
To github.com:brady-richards/openbrain.git
   396895e..2e8a658  main -> main
Already up to date.
[33m⚠ pre-commit: .claude/skills/hire/SKILL.md: missing frontmatter[0m
[33m1 warning(s) — commit proceeding anyway (warn-only mode)[0m
[main f30ba2e] auto: vault update (1 file changed, 2 insertions(+))
 1 file changed, 2 insertions(+)
To github.com:brady-richards/openbrain.git
   2e8a658..f30ba2e  main -> main
sign_and_send_pubkey: signing failed for ED25519 "/Users/brichards/.ssh/id_ed25519" from agent: communication with agent failed
git@github.com: Permission denied (publickey).
fatal: Could not read from remote repository.

Please make sure you have the correct access rights
and the repository exists.
```
