"""Simple Pydantic-AI Agent Demo
============================

This example demonstrates how to create a basic AI agent using Pydantic-AI.
The agent acts as a helpful Python programming assistant.
"""

import asyncio

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

# Create a simple agent with a system prompt
# The Agent automatically handles conversation flow and type safety
python_tutor = Agent(
    model=OpenAIModel("gpt-4o"),  # OpenAI model
    system_prompt="""You are a friendly Python programming tutor. 
    
    Your goal is to help beginners learn Python concepts by:
    - Explaining concepts clearly and simply
    - Providing practical examples
    - Suggesting best practices
    - Being encouraging and supportive
    
    Keep your responses concise but helpful.""",
)


async def demo_simple_agent():
    """Demonstrate basic agent functionality"""
    print("🐍 Python Tutor Agent Demo")
    print("=" * 40)

    # Example questions to demonstrate the agent
    questions = [
        "What's the difference between a list and a tuple in Python?",
        "How do I handle exceptions in Python?",
        "What are Python decorators and when should I use them?",
        "Show me how to read a file in Python safely.",
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n🤔 Question {i}: {question}")
        print("-" * 50)

        # Get response from the agent
        # The agent handles the conversation context automatically
        result = await python_tutor.run(question)

        print(f"🤖 Tutor: {result.output}")

        # Add a small delay for demonstration
        await asyncio.sleep(1)


async def interactive_demo():
    """Interactive demo where user can ask questions"""
    print("\n" + "=" * 50)
    print("🔄 Interactive Mode - Ask your Python questions!")
    print("Type 'quit' to exit")
    print("=" * 50)

    while True:
        try:
            user_question = input("\n🤔 Your question: ").strip()

            if user_question.lower() in ["quit", "exit", "q"]:
                print("👋 Thanks for learning with us!")
                break

            if not user_question:
                print("Please ask a question or type 'quit' to exit.")
                continue

            print("🤖 Thinking...")
            result = await python_tutor.run(user_question)
            print(f"🤖 Tutor: {result.output}")

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Please try again or type 'quit' to exit.")


if __name__ == "__main__":
    print("🚀 Starting Pydantic-AI Simple Agent Demo")
    print("\nNote: Make sure you have set your OPENAI_API_KEY environment variable")
    print("or modify the model to use a local model like 'ollama:llama3'\n")

    # Run the demo
    asyncio.run(demo_simple_agent())

    # Run interactive mode
    asyncio.run(interactive_demo())
