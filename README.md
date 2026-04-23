# kb-plugin

Official Claude Code + Cowork plugin for the **Alzado AI Knowledge Base platform**. Delivers ~80 skills and ~55 sub-agents that run against a hosted KB backend — no repo clone needed.

## Install

In Claude Code or Cowork:

```
/plugin marketplace add alzado-AI/kb-plugin
/plugin install kb
```

Then, in your terminal:

```
pip install kb-cli
kb auth login
```

See [`plugins/kb/.claude-plugin/marketplace-README.md`](plugins/kb/.claude-plugin/marketplace-README.md) for the full setup guide (auth flow, multi-tenant, CLAUDE.md template).

## What's inside

- **`plugins/kb/skills/`** — ~80 workshop and workflow skills (`/kb:program`, `/kb:batman`, `/kb:busca`, `/kb:calendario`, etc.)
- **`plugins/kb/agents/`** — ~55 specialized sub-agents (`doc-writer`, `meeting-parser`, `browser-navigator`, etc.)
- **`plugins/kb/.claude-plugin/claude-md-template.md`** — transversal rules to copy into your `~/.claude/CLAUDE.md`
- **`.claude-plugin/marketplace.json`** — marketplace catalog so this repo works with `/plugin marketplace add`

## Source of truth

Skills and agents are authored in the private `alzado-AI/core-test` monorepo and synced to this public mirror. See [`SYNC.md`](SYNC.md) for the publishing workflow.

## License

MIT. See [`LICENSE`](LICENSE).
