# SkyKnit 2.0 Architecture - Blanket Generator

## Overview
SkyKnit 2.0 is an AI agent system for creating knitting patterns. The initial implementation focuses exclusively on **blankets** - rectangular items with borders that are easier to validate and perfect for proving the concept.

## Core Workflow

```
User Input → Requirements Agent → Fabric Agent → Stitch Agent → Validation Agent → Output
```

**Future Extension** (for 3D garments):
```
User Input → Requirements Agent → Fabric Agent → Stitch Agent → Construction Agent → Validation Agent → Output
```

## Agent Architecture

### 1. Requirements Agent
**Purpose**: Parse and understand user requirements
- Extracts project type (blanket), dimensions, and style preferences
- Clarifies ambiguous requests through follow-up questions
- Outputs a structured requirements object

### 2. Fabric Agent
**Purpose**: Make high-level material and stitch pattern decisions
- Determines yarn weight fiber content
- Selects construction techniques based on desired properties (cables for structure, lace for drape)
- Chooses stitch patterns that achieve desired aesthetic and functional goals
- Estimates gague based on yarn weight and stitch patterns
- Outputs fabric specification with material and construction decisions

### 3. Stitch Agent
**Purpose**: Generate detailed stitch-by-stitch instructions
- Converts fabric specifications into row-by-row knitting instructions
- Handles cast-on, pattern repeats, and bind-off sequences
- Generates clear, step-by-step instructions
- Creates stitch charts when beneficial
- Outputs complete pattern instructions

### 4. Construction Agent *(Future - for 3D garments)*
**Purpose**: Handle shaping and assembly for non-rectangular items
- Calculates shaping (increases/decreases for sleeves, necklines, etc.)
- Determines seaming vs seamless construction
- Plans assembly order and techniques
- Considers 3D form (ease, fit, drape)
- *Bypassed for current rectangular patterns*

### 5. Validation Agent
**Purpose**: Verify pattern accuracy and feasibility
- Checks mathematical consistency of stitch counts
- Validates construction logic and technique compatibility
- Ensures pattern clarity and completeness
- Suggests improvements or catches errors

### 6. Output Agent
**Purpose**: Format and present the final pattern
- Generates multiple output formats (PDF, text, charts)
- Adds helpful diagrams and schematics
- Includes material requirements and gauge info
- Creates beginner-friendly explanations when needed

## Data Models

### RequirementsSpec
- project_type: string
- size: string | object
- style_preferences: object
- special_requirements: array

### DesignSpec
- construction_method: string
- measurements: object
- stitch_patterns: array
- shaping_plan: object
- yarn_requirements: object

### PatternSpec
- instructions: array
- charts: array
- assembly: array
- finishing: array
- materials: object

## Agent Communication
Agents communicate through structured message passing with typed interfaces. Each agent validates inputs and outputs to ensure data consistency throughout the workflow.