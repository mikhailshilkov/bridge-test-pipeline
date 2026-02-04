# Bridge Test Pipeline

Simple test pipeline for the bridge sidecar elimination prototype.

## Steps

1. **hello_code_step** - Simple code step that transforms input (no agent)
2. **hello_agent_step** - Agent step that uses the sidecar to run an agent

## Setup

```bash
uv venv
uv sync
```

## Test locally

```bash
# Check setup
.venv/bin/python main.py check

# Get DSL (step definitions)
.venv/bin/python main.py config get-dsl

# Run a step
.venv/bin/python main.py run --step hello_code_step --input '{"message": "hello"}' --results '{}'
```

