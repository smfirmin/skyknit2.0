# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Skyknit2.0 is an AI agent system for generating knitting patterns. It uses a multi-agent architecture to transform natural language requests into complete, validated knitting patterns with multiple output formats.

## Current Priority: Interactive Design Agent

**Goal**: Make the design agent interactive and robust with iterative user conversations before moving to other parts of the project.

### Development Plan for Interactive Design Agent

#### Phase 1: Core Interactive Logic (No UI needed initially)
**Goal**: Design agent can have a conversation with the user to refine requirements

**Key Components**:
1. **Conversation State Management**: Track the current state of the design discussion
2. **Suggestion Engine**: Generate design suggestions based on partial requirements
3. **Clarification System**: Ask specific questions when requirements are unclear/incomplete
4. **Validation & Feedback Loop**: Present design options and get user feedback

**Testing**: Can be done with simple console I/O or unit tests with mock conversations

#### Phase 2: Conversation Flow Design
**Goal**: Define the interaction patterns

**Key Decisions**:
- What questions to ask and in what order?
- How to present options (A/B choices vs open-ended)?
- When to move from exploration to confirmation?
- How to handle conflicting requirements?

#### Phase 3: Implementation & Testing
**Goal**: Build the interactive system

**Testing Strategy**: 
- **Unit tests**: Mock conversations with predefined user responses
- **Console interface**: Simple CLI for manual testing
- **UI later**: Once the logic is solid, a UI becomes valuable for user experience

#### Design Decisions to Make:

1. **Conversation Style**: Should it be:
   - Guided (agent asks specific questions in sequence)
   - Exploratory (agent makes suggestions, user reacts)
   - Mixed approach?

2. **User Input**: How much knitting knowledge should we assume the user has?

3. **Suggestion Granularity**: Should suggestions be:
   - High-level (yarn weight, pattern complexity)
   - Detailed (specific stitch patterns, exact dimensions)
   - Progressive (start broad, get specific)?

**Recommendation**: Start with Phase 1 using console-based testing. A UI isn't critical initially - we can test the conversation logic thoroughly with scripted interactions. The UI becomes valuable once we nail the conversation flow.

## Notes for Future Development

- **Construction Agent**: Planned for 3D garments (sweaters, hats, etc.)
- **Extensible design**: RAG architecture will enable unlimited pattern expansion
- **Scope decisions**: Knowledge bases will restore removed functionality (skill levels, etc.)
- **Pattern library**: Database + knowledge-driven approach replaces hardcoded limitations