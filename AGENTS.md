## Rules

- Fail fast, do not hide errors, do not walk around to skip or bypass any steps or tests.
- If being asked to commit changes, commit with `git commit -m "<message>"`.
  - Commit with the current Author (check previous commits to see the author).
  - To specify that the commit is from AI, add `[AI]` prefix to the commit message.
- All data is stored in the `data/` directory. DO NOT commit any data to the repository.
- All temporary-ephemeral files are stored in the `.ai/tmp/` directory.
- For Opencode agent, do not try to parallelize the work, just do one task at a time sequentially.
- Before finishing works, make sure the command `make ci` passes.