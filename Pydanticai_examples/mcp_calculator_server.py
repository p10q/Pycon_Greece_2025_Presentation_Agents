"""MCP Calculator Server
====================

A real Model Context Protocol (MCP) server that provides mathematical calculation services.
This server follows MCP specification and can be used by Pydantic-AI agents or any MCP client.

Run this server first, then run the agent that connects to it.

Usage:
    python mcp_calculator_server.py

The server will start on http://localhost:8080
"""

import math
import re
from datetime import datetime
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# MCP Protocol Models
class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    method: str
    params: dict[str, Any] = {}


class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    result: dict[str, Any] = {}
    error: dict[str, Any] = None


class CalculationRequest(BaseModel):
    expression: str


class CalculationResult(BaseModel):
    expression: str
    result: float
    operation_type: str
    explanation: str
    timestamp: str
    server_info: dict[str, str]


# Initialize FastAPI app for MCP server
app = FastAPI(
    title="MCP Calculator Server",
    description="Model Context Protocol server for mathematical calculations",
    version="1.0.0",
)


class MCPCalculatorServer:
    """MCP Calculator Server implementation"""

    def __init__(self):
        self.server_name = "MCP Calculator Server"
        self.version = "1.0.0"
        self.capabilities = {
            "tools": ["calculate", "supported_operations"],
            "operations": [
                "add",
                "subtract",
                "multiply",
                "divide",
                "power",
                "sqrt",
                "abs",
                "round",
            ],
        }

    async def calculate_expression(self, expression: str) -> CalculationResult:
        """Perform mathematical calculations with detailed results

        Args:
            expression: Mathematical expression (e.g., "15 * 23", "sqrt(144)", "2^8")

        Returns:
            CalculationResult: Structured calculation result

        """
        try:
            clean_expr = expression.strip()
            original_expr = clean_expr

            # Handle different mathematical operations
            if "sqrt(" in clean_expr:
                # Extract number from sqrt(number)
                match = re.search(r"sqrt\(([0-9.]+)\)", clean_expr)
                if match:
                    number = float(match.group(1))
                    result = math.sqrt(number)
                    operation_type = "square_root"
                    explanation = f"Square root of {number} equals {result}"
                else:
                    raise ValueError("Invalid sqrt syntax")

            elif "^" in clean_expr:
                # Handle power operations (base^exponent)
                parts = clean_expr.split("^")
                if len(parts) == 2:
                    base = float(parts[0].strip())
                    exponent = float(parts[1].strip())
                    result = base**exponent
                    operation_type = "exponentiation"
                    explanation = (
                        f"{base} raised to the power of {exponent} equals {result}"
                    )
                else:
                    raise ValueError("Invalid power syntax")

            elif "*" in clean_expr:
                # Handle multiplication
                parts = clean_expr.split("*")
                if len(parts) == 2:
                    a = float(parts[0].strip())
                    b = float(parts[1].strip())
                    result = a * b
                    operation_type = "multiplication"
                    explanation = f"{a} multiplied by {b} equals {result}"
                else:
                    raise ValueError("Invalid multiplication syntax")

            elif "+" in clean_expr:
                # Handle addition
                parts = clean_expr.split("+")
                if len(parts) == 2:
                    a = float(parts[0].strip())
                    b = float(parts[1].strip())
                    result = a + b
                    operation_type = "addition"
                    explanation = f"{a} plus {b} equals {result}"
                else:
                    raise ValueError("Invalid addition syntax")

            elif "-" in clean_expr and clean_expr.count("-") == 1:
                # Handle subtraction (but not negative numbers)
                parts = clean_expr.split("-")
                if len(parts) == 2 and parts[0].strip():
                    a = float(parts[0].strip())
                    b = float(parts[1].strip())
                    result = a - b
                    operation_type = "subtraction"
                    explanation = f"{a} minus {b} equals {result}"
                else:
                    raise ValueError("Invalid subtraction syntax")

            elif "/" in clean_expr:
                # Handle division
                parts = clean_expr.split("/")
                if len(parts) == 2:
                    a = float(parts[0].strip())
                    b = float(parts[1].strip())
                    if b == 0:
                        raise ValueError("Division by zero is not allowed")
                    result = a / b
                    operation_type = "division"
                    explanation = f"{a} divided by {b} equals {result}"
                else:
                    raise ValueError("Invalid division syntax")

            elif "abs(" in clean_expr:
                # Handle absolute value
                match = re.search(r"abs\(([0-9.-]+)\)", clean_expr)
                if match:
                    number = float(match.group(1))
                    result = abs(number)
                    operation_type = "absolute_value"
                    explanation = f"Absolute value of {number} equals {result}"
                else:
                    raise ValueError("Invalid abs syntax")

            else:
                # Fallback: strictly parse simple numeric literals only
                try:
                    # Accept only plain numeric literals (no operators)
                    if re.fullmatch(r"[-+]?\d+(\.\d+)?", clean_expr):
                        result = float(clean_expr)
                        operation_type = "numeric_literal"
                        explanation = f"Parsed numeric literal {clean_expr}"
                    else:
                        raise ValueError("Unsupported expression syntax")
                except Exception as parse_err:
                    raise ValueError(
                        f"Unsupported expression: {clean_expr}",
                    ) from parse_err

            return CalculationResult(
                expression=original_expr,
                result=result,
                operation_type=operation_type,
                explanation=explanation,
                timestamp=datetime.now().isoformat(),
                server_info={
                    "server": self.server_name,
                    "version": self.version,
                    "method": "mcp_calculation",
                },
            )

        except Exception as e:
            # Return error as a CalculationResult with zero result
            return CalculationResult(
                expression=expression,
                result=0.0,
                operation_type="error",
                explanation=f"Error calculating '{expression}': {e!s}",
                timestamp=datetime.now().isoformat(),
                server_info={
                    "server": self.server_name,
                    "version": self.version,
                    "method": "mcp_calculation",
                    "error": str(e),
                },
            )


# Create MCP server instance
mcp_server = MCPCalculatorServer()


# MCP Protocol Endpoints
@app.get("/")
async def server_info():
    """MCP server information endpoint"""
    return {
        "server": mcp_server.server_name,
        "version": mcp_server.version,
        "protocol": "Model Context Protocol (MCP)",
        "capabilities": mcp_server.capabilities,
        "endpoints": {
            "calculate": "POST /mcp/calculate",
            "capabilities": "GET /mcp/capabilities",
            "health": "GET /health",
        },
        "status": "running",
    }


@app.get("/mcp/capabilities")
async def get_capabilities():
    """MCP capabilities endpoint"""
    return {
        "capabilities": mcp_server.capabilities,
        "tools": [
            {
                "name": "calculate",
                "description": "Perform mathematical calculations",
                "parameters": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate",
                        "examples": ["15 * 23", "sqrt(144)", "2^8", "100 + 25.5"],
                    },
                },
            },
            {
                "name": "supported_operations",
                "description": "Get list of supported mathematical operations",
                "parameters": {},
            },
        ],
    }


@app.post("/mcp/calculate")
async def mcp_calculate(request: CalculationRequest):
    """MCP calculate tool endpoint

    This is the main MCP tool that performs mathematical calculations
    """
    try:
        result = await mcp_server.calculate_expression(request.expression)
        return {"tool": "calculate", "result": result.dict(), "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Calculation error: {e!s}")


@app.get("/mcp/supported_operations")
async def get_supported_operations():
    """Get list of supported mathematical operations"""
    return {
        "operations": mcp_server.capabilities["operations"],
        "examples": {
            "addition": "15 + 23",
            "subtraction": "50 - 12",
            "multiplication": "15 * 23",
            "division": "100 / 4",
            "exponentiation": "2^8",
            "square_root": "sqrt(144)",
            "absolute_value": "abs(-15)",
        },
        "syntax_notes": [
            "Use ^ for exponentiation (e.g., 2^8)",
            "Use sqrt(number) for square root",
            "Use abs(number) for absolute value",
            "Basic operations: +, -, *, /",
            "Spaces around operators are optional",
        ],
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "server": mcp_server.server_name,
        "version": mcp_server.version,
        "uptime": "running",
        "capabilities_count": len(mcp_server.capabilities["tools"]),
    }


# Development server runner
def run_server():
    """Run the MCP calculator server"""
    print("🧮 Starting MCP Calculator Server")
    print("=" * 40)
    print(f"Server: {mcp_server.server_name}")
    print(f"Version: {mcp_server.version}")
    print("URL: http://localhost:8080")
    print("Capabilities: http://localhost:8080/mcp/capabilities")
    print("Health: http://localhost:8080/health")
    print("=" * 40)
    print("🔧 Ready to serve mathematical calculations via MCP!")
    print("💡 Use this server with Pydantic-AI agents or any MCP client")
    print()

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")


if __name__ == "__main__":
    run_server()
