# alzadi-kb — CLI for the Alzadi KB platform

Multi-tenant context switching, device-flow auth, and HTTP wrappers around
the hosted Django REST API. Ships with the Claude Code plugin at
[alzado-AI/kb-plugin](https://github.com/alzado-AI/kb-plugin).

## Install

From PyPI:

```bash
pip install alzadi-kb
```

Or straight from this repo (no PyPI account required):

```bash
pip install "git+https://github.com/alzado-AI/kb-plugin.git#subdirectory=cli"
```

## Use

```bash
kb auth login          # opens browser, pick tenant, confirm
kb auth status
kb search "<keyword>"
kb --help              # full list of subcommands
```

See the [plugin README](../plugins/kb/.claude-plugin/marketplace-README.md) for
the full onboarding (plugin install + CLI install + auth flow).
