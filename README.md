# Skyknit 2.0

[![CI](https://github.com/sfirmin/skyknit2.0/workflows/CI/badge.svg)](https://github.com/sfirmin/skyknit2.0/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/sfirmin/skyknit2.0/branch/main/graph/badge.svg)](https://codecov.io/gh/sfirmin/skyknit2.0)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

An AI agent system that generates complete knitting patterns from natural language requests.

## Overview

Skyknit 2.0 transforms user requests like "I want a simple blanket" into complete, validated knitting patterns with multiple output formats. Built with a multi-agent architecture for clear separation of concerns and extensible design.

## Features

- **Natural Language Input**: Simple requests like "cable blanket" or "simple blanket"
- **Complete Pattern Generation**: Cast-on counts, stitch instructions, materials list, gauge
- **Mathematical Validation**: Automatic dimension accuracy checking and pattern verification
- **Multiple Output Formats**: Markdown, plain text, JSON, and summary formats
- **Yarn Calculation**: Automatic yardage estimation with waste buffer

## Current Capabilities

### Supported Projects
- **Blankets**: Rectangular patterns with automatic seed stitch borders
- **Pattern Types**: Stockinette (simple) and cable patterns
- **Sizes**: Configurable dimensions (default 48" x 60")

### Pattern Features
- Automatic gauge calculations (worsted weight default)
- Pattern repeat adjustments for cables
- Border integration with main pattern
- Construction notes and finishing instructions

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

**Current Status**: 188/188 tests passing, 90% code coverage, comprehensive error handling

## Architecture

Multi-agent system with specialized responsibilities:

1. **Requirements Agent** → Parses user input into structured requirements
2. **Fabric Agent** → Makes material and construction decisions  
3. **Construction Agent** → Plans structural approach and construction zones
4. **Stitch Agent** → Generates mathematical calculations and instructions
5. **Validation Agent** → Verifies pattern accuracy and provides warnings
6. **Output Agent** → Calculates yardage and formats final patterns

## Example Output

Input: `"I want a simple blanket"`

Output includes:
- **Materials**: 8640 yards worsted weight wool yarn, US 8 needles
- **Gauge**: 4 stitches and 5.5 rows = 1 inch
- **Instructions**: Cast on 200 stitches, work stockinette with borders
- **Finished Size**: 50" x 60" (accounting for border width)

## Future Development

- LLM integration for dynamic pattern generation
- Support for additional project types (scarves, sweaters, hats)
- Advanced stitch pattern library
- Construction agents for 3D garments

## References

Inspired by MIT's computational knitting research:
- https://www.zdnet.com/article/mit-breaks-new-ground-in-ai-with-knitting-yes-knitting/
- https://deepknitting.csail.mit.edu/
- https://knitskel.csail.mit.edu/