# Skyknit 2.0

[![CI](https://github.com/sfirmin/skyknit2.0/workflows/CI/badge.svg)](https://github.com/sfirmin/skyknit2.0/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/sfirmin/skyknit2.0/branch/main/graph/badge.svg)](https://codecov.io/gh/sfirmin/skyknit2.0)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

An AI agent system that generates complete knitting patterns from natural language requests.

## Overview

Skyknit 2.0 transforms user requests like "I want a simple blanket" into complete, validated knitting patterns with multiple output formats. Built with a multi-agent architecture for clear separation of concerns and extensible design.

## Quick Start

```python
from src.workflow.pattern_workflow import PatternWorkflow

# Initialize the workflow
workflow = PatternWorkflow()

# Generate a pattern
result = workflow.generate_pattern("I want a cable blanket")

# Access the formatted pattern
markdown_pattern = result["outputs"]["markdown"]
print(markdown_pattern)
```

## Testing

Run the complete test suite:

```bash
# Setup environment (with conda)
conda env create -f environment.yml
conda activate skyknit

# Or setup manually
conda create -n skyknit python=3.12 -y
conda activate skyknit
pip3 install -r requirements.txt
pip3 install ruff

# Run tests with coverage
python3 -m pytest --cov=src --cov-report=term-missing

# Run linting and formatting
python3 -m ruff check .
python3 -m ruff format .

# Just the end-to-end tests
python3 -m pytest tests/test_end_to_end.py -v
```

## The O.G.
https://www.aiweirdness.com/skyknit-when-knitters-teamed-up-with-18-04-19/

## References

Inspired by MIT's computational knitting research:
- https://www.zdnet.com/article/mit-breaks-new-ground-in-ai-with-knitting-yes-knitting/
- https://deepknitting.csail.mit.edu/
- https://knitskel.csail.mit.edu/


## Potential Knowledge Base Resources

- https://www.knittingfool.com/StitchIndex/Alpha.aspx
- http://knittingonthenet.com/stitches.htm
- https://nimble-needles.com/knitting-stitches-and-patterns/
