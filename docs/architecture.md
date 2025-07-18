# SkyKnit 2.0 Architecture - Blanket Generator

## Overview
SkyKnit 2.0 is an AI agent system for creating knitting patterns. 

## Core Workflow

```
User Input → Design Agent → Construction Agent → Stitch Agent → Validation Agent → Output
```

## Agent Architecture

### 1. Design Agent
**Purpose**: Parse and understand user requirements, collaborate with user to create a design.
- Extracts project type (blanket), dimensions, and style preferences
- Clarifies ambiguous requests through follow-up questions
- Determines yarn weight fiber content
- Selects construction techniques based on desired properties (cables for structure, lace for drape)
- Chooses stitch patterns that achieve desired aesthetic and functional goals
- Estimates gague based on yarn weight and stitch patterns
- Outputs a structured design object


### 2. Construction Agent *(Future - for 3D garments)*
**Purpose**: Handle shaping and assembly for non-rectangular items
- Calculates shaping (increases/decreases for sleeves, necklines, etc.)
- Determines seaming vs seamless construction
- Plans assembly order and techniques
- Considers 3D form (ease, fit, drape)
- *Bypassed for current rectangular patterns*

### 3. Stitch Agent
**Purpose**: Generate detailed stitch-by-stitch instructions
- Converts fabric specifications into row-by-row knitting instructions
- Handles cast-on, pattern repeats, and bind-off sequences
- Generates clear, step-by-step instructions
- Creates stitch charts when beneficial
- Outputs complete pattern instructions

### 4. Validation Agent
**Purpose**: Verify pattern accuracy and feasibility
- Checks mathematical consistency of stitch counts
- Validates construction logic and technique compatibility
- Ensures pattern clarity and completeness
- Suggests improvements or catches errors

### 5. Output Agent
**Purpose**: Format and present the final pattern
- Generates multiple output formats (PDF, text, charts)
- Adds helpful diagrams and schematics
- Includes material requirements and gauge info
- Creates beginner-friendly explanations when needed

## Data Models

### DesignSpec
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