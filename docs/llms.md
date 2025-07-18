# LLM Integration Setup

This document explains how to set up and use the LLM-powered features in Skyknit2.0.

## Quick Start Options

### Option 1: Ollama (Local, Private, Free)

1. **Install Ollama:**
   Visit https://ollama.ai and install for your platform

2. **Pull a model:**
   ```bash
   ollama pull gemma3:4b
   ```

3. **Start using (no configuration needed):**
   ```python
   client = LLMClient.create_ollama()
   ```

### Option 2: Anthropic Claude (Cloud API)

1. **Copy the credentials template:**
   ```bash
   cp credentials.json.example credentials.json
   ```

2. **Add your Anthropic API key:**
   ```json
   {
     "anthropic": {
       "api_key": "your-anthropic-api-key-here"
     }
   }
   ```

3. **Install Anthropic SDK:**
   ```bash
   pip install anthropic
   ```

## Usage

### With Ollama Local Models (Offline)

```python
from src.llm import LLMClient
from src.llm.llm_requirements_agent import RequirementsAgent

# Create Ollama-powered agent (completely local)
client = LLMClient.create_ollama()
agent = RequirementsAgent(llm_client=client)

# Parse natural language requests
result = agent.process({
    "user_request": "I want a cozy cable blanket for winter"
})

print(f"Project: {result['requirements'].project_type.value}")
print(f"Dimensions: {result['requirements'].dimensions.width}\" x {result['requirements'].dimensions.length}\"")
```

### With Anthropic Claude (Cloud API)

```python
from src.llm import LLMClient
from src.llm.llm_requirements_agent import RequirementsAgent

# Create Anthropic-powered agent
client = LLMClient.create_anthropic()
agent = RequirementsAgent(llm_client=client)

# Same API as Ollama
result = agent.process({
    "user_request": "I want a cozy cable blanket for winter"
})
```

## Security

- `credentials.json` is automatically ignored by git
- Ollama runs completely local - no data leaves your machine
- Never commit API keys to the repository
- Use environment variables in production if needed

## Supported Models

Currently supports:
- **Ollama Local Models** (gemma3:4b, llama3.2, qwen2.5-coder, etc.)
- **Anthropic Claude 3 Haiku** (fast and cost-effective cloud API)

## Recommended Models for Ollama

- **gemma3:4b** - Good balance of quality and speed (default)
- **llama3.2:3b** - Faster, smaller model