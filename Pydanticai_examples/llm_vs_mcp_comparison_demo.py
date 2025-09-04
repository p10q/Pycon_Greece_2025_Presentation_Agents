"""LLM vs MCP Calculator Comparison Demo
=====================================

This script demonstrates the accuracy difference between:
1. LLM doing math calculations itself (often inaccurate)
2. MCP Calculator Server doing precise calculations

Perfect for presentations to show why external tools matter!

Usage:
1. First start the MCP server: python mcp_calculator_server.py
2. Then run this demo: python llm_vs_mcp_comparison_demo.py
"""

import asyncio

import httpx
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel


# Result model for structured output
class MathResult(BaseModel):
    """Structured math calculation result"""

    question: str = Field(..., description="The math question asked")
    expression: str = Field(..., description="Mathematical expression")
    result: float = Field(..., description="Calculation result")
    explanation: str = Field(..., description="Step-by-step explanation")
    method: str = Field(..., description="Calculation method used")


# LLM-only math agent (no external tools)
llm_math_agent = Agent(
    model=OpenAIModel("gpt-3.5-turbo"),
    output_type=MathResult,
    system_prompt="""You are a mathematician. Calculate mathematical expressions using ONLY your own knowledge.
    DO NOT use any external tools or calculators. Do the math yourself step by step.
    Show your working and provide the final numerical result. Set method to 'LLM Internal Calculation'.""",
)

# MCP-enabled math agent
mcp_math_agent = Agent(
    model=OpenAIModel("gpt-4o"),
    output_type=MathResult,
    system_prompt="""You are a mathematician with access to a precise MCP calculator tool.
    ALWAYS use the mcp_calculate tool for mathematical operations rather than doing them yourself.
    Provide the question and explain what calculation was performed. Set method to 'MCP Calculator Server' ALWAYS.""",
)


@mcp_math_agent.tool_plain
async def mcp_calculate(expression: str) -> dict:
    """Use MCP Calculator Server for precise mathematical calculations.

    Args:
        expression: Mathematical expression (e.g., "47 * 83", "sqrt(289)")

    Returns:
        dict: Calculation result from MCP server

    """
    try:
        MCP_SERVER_URL = "http://localhost:8080"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MCP_SERVER_URL}/mcp/calculate",
                json={"expression": expression},
                timeout=10.0,
            )

            if response.status_code == 200:
                mcp_result = response.json()
                calc_data = mcp_result["result"]

                return {
                    "result": calc_data["result"],
                    "explanation": calc_data["explanation"],
                    "expression": calc_data["expression"],
                    "server": calc_data["server_info"]["server"],
                    "status": "success",
                }
            return {"error": f"MCP server error: {response.status_code}"}

    except httpx.ConnectError:
        return {
            "error": "Cannot connect to MCP server. Please start it with: python mcp_calculator_server.py",
            "result": 0,
            "explanation": "MCP server is offline",
        }
    except Exception as e:
        return {
            "error": f"Error: {e!s}",
            "result": 0,
            "explanation": "Calculation failed",
        }


async def compare_calculations():
    """Main demo comparing LLM vs MCP calculations"""
    print("🎯 LLM vs MCP Calculator Accuracy Comparison")
    print("=" * 60)
    print("This demo shows why AI agents need external tools for math!")
    print("=" * 60)

    # Math questions that often trip up LLMs (much more challenging!)
    test_questions = [
        {"question": "What is 7,834 multiplied by 9,267?", "expression": "7834 * 9267"},
        {"question": "Calculate 127 raised to the power of 4", "expression": "127^4"},
        {"question": "What is the square root of 87,489?", "expression": "sqrt(87489)"},
        {"question": "Divide 123,456,789 by 4,567", "expression": "123456789 / 4567"},
    ]

    for i, test in enumerate(test_questions, 1):
        print(f"\n{'🔢 QUESTION ' + str(i):=^60}")
        print(f"❓ {test['question']}")
        print(f"📝 Expression: {test['expression']}")
        print("=" * 60)

        # LLM Calculation
        print("\n🤖 LLM CALCULATION (AI doing math itself)")
        print("-" * 50)
        try:
            llm_result = await llm_math_agent.run(test["question"])
            llm_calc: MathResult = llm_result.output

            print(f"🎯 LLM Result: {llm_calc.result}")
            print(f"📝 LLM Explanation: {llm_calc.explanation}")
            print(f"⚡ Method: {llm_calc.method}")

        except Exception as e:
            print(f"❌ LLM Error: {e}")
            llm_calc = None

        # MCP Server Calculation
        print("\n🔧 MCP CALCULATION (External precise tool)")
        print("-" * 50)
        try:
            mcp_result = await mcp_math_agent.run(test["question"])
            mcp_calc: MathResult = mcp_result.output

            print(f"🎯 MCP Result: {mcp_calc.result}")
            print(f"📝 MCP Explanation: {mcp_calc.explanation}")
            print(f"⚡ Method: {mcp_calc.method}")
            print("✅ Powered by: MCP Calculator Server")

        except Exception as e:
            print(f"❌ MCP Error: {e}")
            mcp_calc = None

        # Comparison Summary
        print("\n📊 COMPARISON SUMMARY")
        print("-" * 30)
        if llm_calc and mcp_calc:
            if abs(llm_calc.result - mcp_calc.result) < 0.001:
                print("✅ Both methods agree!")
            else:
                print("⚠️  DIFFERENT RESULTS!")
                print(f"   LLM: {llm_calc.result}")
                print(f"   MCP: {mcp_calc.result}")
                print("   🎯 MCP is typically more accurate!")

        print("🔹" * 60)

        # Pause for presentation
        if i < len(test_questions):
            input("\n👆 Press Enter to continue to next question...")


async def presentation_summary():
    """Final summary for presentation"""
    print("\n" + "🎯" * 60)
    print("📈 PRESENTATION SUMMARY")
    print("🎯" * 60)
    print()
    print("🔍 What we demonstrated:")
    print("   • LLMs can struggle with mathematical calculations")
    print("   • External MCP tools provide precise, reliable results")
    print("   • Pydantic-AI agents can seamlessly use both approaches")
    print()
    print("💡 Key Takeaway:")
    print(
        "   📌 AI agents are more powerful when they can use external tools in cases that they are not good only with use of LLMs!",
    )
    print(
        "   📌 MCP (Model Context Protocol) enables reliable tool integration, between plethora of tools",
    )
    print(
        "   📌 Structured outputs ensure type-safe, predictable results, in order to partially fight LLM hallucinations",
    )
    print()
    print(
        "This is why modern AI systems need tool integration in order to be reliable and useful for real-world applications!",
    )
    print("🎯" * 60)


async def check_mcp_server():
    """Check if MCP server is running"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8080/health", timeout=5.0)
            if response.status_code == 200:
                server_info = response.json()
                print("✅ MCP Calculator Server is running!")
                print(f"   Server: {server_info.get('server', 'Unknown')}")
                print(f"   Status: {server_info.get('status', 'Unknown')}")
                return True
    except:
        pass

    print("❌ MCP Calculator Server is not running!")
    print("🔧 Please start it first with: python mcp_calculator_server.py")
    print("⏰ Then run this demo again.")
    return False


if __name__ == "__main__":
    print("🚀 Starting LLM vs MCP Calculator Comparison Demo")
    print("📊 Perfect for presentations showing AI tool integration benefits!")
    print()

    # Check if MCP server is available
    server_running = asyncio.run(check_mcp_server())

    if server_running:
        print("\n🎬 Starting demonstration...")
        input("👆 Press Enter to begin the comparison demo...")

        # Run the comparison demo
        asyncio.run(compare_calculations())

        # Show final summary
        asyncio.run(presentation_summary())
    else:
        print("\n⏸️  Demo paused - please start the MCP server first.")
