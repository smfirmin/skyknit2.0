#!/usr/bin/env python3
"""
Console demo for the interactive DesignAgent.

This provides a simple command-line interface to test the conversation
capabilities of the DesignAgent.
"""

import logging
import sys

from agents.design_agent import DesignAgent
from conversation import ConversationState
from llms import LLMClient


def setup_logging():
    """Setup basic logging for the demo"""
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise in console
        format="%(levelname)s: %(message)s",
    )


def create_agent() -> DesignAgent | None:
    """Create a DesignAgent with an LLM client"""
    try:
        # Try to create an Ollama LLM client
        print("🔌 Connecting to Ollama...")
        llm_client = LLMClient.create_ollama()
        agent = DesignAgent(llm_client=llm_client)
        return agent
    except Exception as e:
        print(f"❌ Failed to create DesignAgent: {e}")
        print("💡 Make sure Ollama is running: ollama serve")
        print("💡 And you have a model installed: ollama pull gemma3:4b")
        return None


def print_welcome():
    """Print welcome message"""
    print("🧶 Welcome to Skyknit2.0 Interactive Design Agent!")
    print("=" * 50)
    print("I'll help you design a knitting pattern through conversation.")
    print("Type 'quit' or 'exit' to end the session.")
    print("Type 'help' for more options.")
    print()


def print_help():
    """Print help information"""
    print("\n📋 Available Commands:")
    print("  quit, exit  - End the conversation")
    print("  help        - Show this help message")
    print("  status      - Show current conversation status")
    print("  restart     - Start a new conversation")
    print()


def print_status(conversation: ConversationState):
    """Print current conversation status"""
    print("\n📊 Conversation Status:")
    print(f"  Phase: {conversation.phase.value}")
    print(f"  Iterations: {conversation.iteration_count}")
    print(f"  Summary: {conversation.get_conversation_summary()}")
    print(f"  Missing: {', '.join(conversation.working_spec.get_missing_fields())}")
    print()


def handle_special_commands(user_input: str, conversation: ConversationState) -> bool:
    """Handle special commands. Returns True if command was handled."""
    command = user_input.lower().strip()

    if command in ["quit", "exit"]:
        print("\n👋 Thanks for using Skyknit2.0! Happy knitting!")
        return True
    elif command == "help":
        print_help()
        return True
    elif command == "status":
        print_status(conversation)
        return True
    elif command == "restart":
        print("\n🔄 Starting a new conversation...")
        return True

    return False


def run_conversation(agent: DesignAgent):
    """Run the main conversation loop"""
    conversation = None

    while True:
        try:
            if conversation is None:
                # Start new conversation
                print("🤖 Agent: What knitting project would you like to create?")
                user_input = input("👤 You: ").strip()

                if not user_input:
                    continue

                if handle_special_commands(user_input, ConversationState()):
                    if user_input.lower() in ["quit", "exit"]:
                        break
                    continue

                # Start conversation
                print("🤔 Thinking...")
                conversation = agent.start_conversation(user_input)

                # Get first response
                conversation, response, is_complete = agent.continue_conversation(
                    conversation, user_input
                )

                print(f"🤖 Agent: {response}")

                if is_complete:
                    print("\n✅ Design complete! Your pattern is ready.")
                    conversation = None
                    continue

            else:
                # Continue existing conversation
                user_input = input("👤 You: ").strip()

                if not user_input:
                    continue

                if handle_special_commands(user_input, conversation):
                    if user_input.lower() in ["quit", "exit"]:
                        break
                    elif user_input.lower() == "restart":
                        conversation = None
                        continue
                    else:
                        continue

                # Process response
                print("🤔 Thinking...")
                conversation, response, is_complete = agent.continue_conversation(
                    conversation, user_input
                )

                print(f"🤖 Agent: {response}")

                if is_complete:
                    print("\n✅ Design complete! Your pattern is ready.")
                    print("Type 'restart' to design another pattern.")
                    conversation = None

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ An error occurred: {e}")
            print("The conversation will continue...")


def main():
    """Main entry point"""
    setup_logging()
    print_welcome()

    # Create agent
    agent = create_agent()
    if not agent:
        print("❌ Could not start the design agent. Please check your setup.")
        sys.exit(1)

    print("✅ Design agent ready!")
    print()

    # Run conversation
    try:
        run_conversation(agent)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        agent.close()


if __name__ == "__main__":
    main()
