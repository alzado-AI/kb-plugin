# kb CLI

Python CLI for the KB platform — multi-tenant context switching, device-flow
auth, and HTTP wrappers around the hosted Django REST API.

## Install

```bash
pip install "git+https://github.com/alzado-AI/kb-plugin.git#subdirectory=cli"
```

## Use

```bash
kb auth login          # opens browser, pick tenant, confirm
kb auth status
kb search "<keyword>"
```

See the plugin README for the full onboarding (plugin install + CLI install + auth).
