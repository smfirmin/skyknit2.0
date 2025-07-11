# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Skyknit2.0 is an AI agent system for generating knitting patterns. It uses a multi-agent architecture to transform natural language requests into complete, validated knitting patterns with multiple output formats.

## Current State

- **Fully implemented** multi-agent pattern generation system
- **Complete test suite** with 90% code coverage (188 tests passing)
- **Comprehensive error handling** with domain-specific exceptions
- **Blanket-only focus** - generates rectangular patterns with automatic borders
- **Production ready** core workflow for simple and cable blanket patterns

## Development Setup

**Technology Stack**: Python 3.12 with pytest for testing, dataclasses for models

**Environment Setup**:
1. Create conda environment: `conda env create -f environment.yml`
2. Activate environment: `conda activate skyknit`
3. Or create manually: `conda create -n skyknit python=3.12 -y && conda activate skyknit`
4. Install dependencies: `pip3 install -r requirements.txt && pip3 install ruff`

**Common Commands** (use with activated environment):
- `python3 -m pytest` - Run all tests
- `python3 -m pytest tests/test_models.py` - Run specific test file
- `python3 -m pytest --cov=src` - Run tests with coverage
- `python3 -m ruff check .` - Run linting checks
- `python3 -m ruff format .` - Format code
- `python3 -m ruff check --fix .` - Fix auto-fixable linting issues

**CI/CD Pipeline**:
- **Automated Testing**: GitHub Actions runs full test suite on every push/PR
- **Code Quality**: Ruff linting and formatting validation
- **Coverage Monitoring**: 85% minimum coverage threshold enforced
- **Security Scanning**: Bandit security analysis and dependency vulnerability checks
- **Multi-Python Support**: Tests on Python 3.11, 3.12, and 3.13
- **Dependency Management**: Automated dependency updates via Dependabot

**Project Structure**:
- `src/models/knitting_models.py` - Core data models (YarnSpec, FabricSpec, PatternSpec, etc.)
- `src/agents/` - Agent implementations with clear separation of concerns
- `src/workflow/pattern_workflow.py` - Main orchestration workflow
- `tests/test_end_to_end.py` - Comprehensive end-to-end test suite

## Architecture Overview

**Multi-agent system with clear separation of concerns:**

- **Requirements Agent**: Parses user requests → structured requirements with dimensions
- **Fabric Agent**: Material decisions → yarn specs, stitch patterns, gauge, construction notes
- **Construction Agent**: Structural planning → construction zones, sequence, finishing requirements
- **Stitch Agent**: Math & instructions → cast-on counts, row calculations, stitch instructions
- **Validation Agent**: Quality assurance → dimension validation, pattern verification, warnings
- **Output Agent**: Final formatting → yardage calculation, multiple output formats

**Data Flow**: User request → Requirements → Fabric decisions → Construction planning → Stitch calculations → Validation → Formatted outputs

**Current capabilities:**
- Simple stockinette blankets with seed stitch borders
- Cable blankets with pattern repeat adjustments
- Automatic dimension validation and mathematical accuracy checking
- Multiple output formats (markdown, text, JSON, summary)

## Recent Architecture Changes

**Data Model Improvements:**
- **Dimensions**: Moved from FabricSpec to RequirementsSpec only
- **Yardage calculation**: Moved from FabricSpec to OutputAgent
- **YarnSpec simplified**: Contains only weight, fiber, color (removed brand/yardage)
- **Validation centralized**: All dimension accuracy checking in ValidationAgent

**Agent Responsibilities:**
- **FabricAgent**: No longer handles dimensions or yardage calculation
- **ConstructionAgent**: NEW - Plans structural approach, construction zones, and sequence
- **StitchAgent**: Gets construction plan, focuses on stitch math + instruction generation
- **ValidationAgent**: Added dimension accuracy validation from StitchAgent
- **OutputAgent**: Now calculates estimated yardage during final pattern generation

## Error Handling

**Comprehensive error handling system with domain-specific exceptions:**

- **Input Validation**: All agents validate inputs and provide clear error messages
- **Mathematical Safety**: Stitch calculations include bounds checking and division-by-zero protection
- **Workflow Orchestration**: Multi-stage error handling with precise failure point identification
- **Custom Exceptions**: Domain-specific error types (ValidationError, GaugeError, DimensionError, etc.)
- **Error Recovery**: Actionable error messages with suggested fixes and supported options

**Key Exception Types:**
- `ValidationError`: Invalid input data with field-specific context
- `GaugeError`: Yarn weight and gauge calculation issues
- `DimensionError`: Invalid or impossible pattern dimensions
- `StitchCalculationError`: Mathematical errors in stitch/row calculations
- `WorkflowOrchestrationError`: Multi-agent workflow failures with stage identification

## Notes for Future Development

- **LLM Integration**: Agents use structured logic ready for LLM replacement
- **Construction Agent**: Planned for 3D garments (sweaters, hats, etc.)
- **Extensible design**: Easy to add new project types and stitch patterns
- **Scope decisions**: Skill levels and scarf functionality removed for focused implementation
- **Pattern library**: Framework ready for expanding beyond stockinette and simple cables