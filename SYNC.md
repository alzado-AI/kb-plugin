# Sync workflow

This repo is a **public mirror** of the skills and agents authored in the private `alzado-AI/core-test` monorepo.

## How updates reach this repo

1. Skills and agents are edited in `core-test/.claude/skills/` and `core-test/.claude/agents/`.
2. A scrub pass removes client-specific mentions (see [`core-test/tools/publish-plugin.sh`](https://github.com/alzado-AI/core-test/blob/main/tools/publish-plugin.sh)).
3. Content is copied into `plugins/kb/skills/` and `plugins/kb/agents/` in this repo.
4. `plugin.json` version is bumped.
5. A commit + tag + push publishes the new version; Claude Code picks it up on next `/plugin update kb`.

## Directory layout

```
kb-plugin/
├── .claude-plugin/
│   └── marketplace.json             # Marketplace catalog (entry point for /plugin marketplace add)
├── plugins/
│   └── kb/
│       ├── .claude-plugin/
│       │   ├── plugin.json              # Plugin manifest
│       │   ├── marketplace-README.md    # User-facing setup guide
│       │   └── claude-md-template.md    # Transversal rules template
│       ├── skills/                      # ~80 skills with SKILL.md files
│       └── agents/                      # ~55 sub-agents + shared/ includes
├── README.md
├── SYNC.md                              # This file
└── LICENSE
```

## Versioning

- Semver in `plugins/kb/.claude-plugin/plugin.json` (e.g., `0.1.0`)
- Same version mirrored in `.claude-plugin/marketplace.json` under the `kb` plugin entry
- Tag releases as `v<version>` (e.g., `v0.1.0`) on main

## Making contributions

This repo does not accept external PRs directly — edits flow from the core-test monorepo. Please file issues on this repo for bugs you find in the published content; the fix will happen upstream.
