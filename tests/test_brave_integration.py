#!/usr/bin/env python3
"""Test script to validate Brave Search MCP integration
"""

import asyncio
import os
import sys

import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


async def test_brave_mcp_server():
    """Test the Brave Search MCP server directly."""
    print("🔍 Testing Brave Search MCP Server...")

    # Check if BRAVE_API_KEY is set
    brave_api_key = os.getenv("BRAVE_API_KEY")
    if not brave_api_key:
        print("❌ BRAVE_API_KEY environment variable is not set")
        print("   Please set your Brave Search API key in the .env file")
        return False

    print("✅ BRAVE_API_KEY is set")

    # Test MCP server endpoints
    base_url = "http://localhost:3001"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test health endpoint
            print(f"🏥 Testing health endpoint: {base_url}/health")
            health_response = await client.get(f"{base_url}/health")

            if health_response.status_code == 200:
                print("✅ Health check passed")
                health_data = health_response.json()
                print(f"   Status: {health_data.get('status')}")
            else:
                print(f"❌ Health check failed: {health_response.status_code}")
                return False

            # Test tools listing
            print(f"🛠️  Testing tools endpoint: {base_url}/tools")
            tools_response = await client.get(f"{base_url}/tools")

            if tools_response.status_code == 200:
                print("✅ Tools listing passed")
                tools_data = tools_response.json()
                tools = tools_data.get("tools", [])
                print(f"   Available tools: {len(tools)}")
                for tool in tools:
                    print(f"   - {tool.get('name')}: {tool.get('description')}")
            else:
                print(f"❌ Tools listing failed: {tools_response.status_code}")
                return False

            # Test brave_web_search tool
            print("🔍 Testing brave_web_search tool...")
            search_payload = {
                "tool": "brave_web_search",
                "parameters": {
                    "query": "Python FastAPI tutorial",
                    "count": 5,
                    "freshness": "pm",
                },
            }

            search_response = await client.post(
                f"{base_url}/tools/brave_web_search",
                json=search_payload,
            )

            if search_response.status_code == 200:
                print("✅ Brave web search test passed")
                search_data = search_response.json()
                results = search_data.get("result", [])
                print(f"   Found {len(results)} search results")

                if results:
                    print("   Sample result:")
                    sample = results[0]
                    print(f"   - Title: {sample.get('title', 'N/A')[:60]}...")
                    print(f"   - URL: {sample.get('url', 'N/A')[:60]}...")
                    print(
                        f"   - Description: {sample.get('description', 'N/A')[:60]}...",
                    )

                return True
            print(f"❌ Brave web search test failed: {search_response.status_code}")
            try:
                error_data = search_response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Response: {search_response.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Connection error: {e}")
        print("   Make sure the Brave Search MCP server is running")
        return False


async def test_main_app_integration():
    """Test the main application integration."""
    print("\n🚀 Testing Main Application Integration...")

    base_url = "http://localhost:8000"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test health endpoint
            print(f"🏥 Testing main app health: {base_url}/health")
            health_response = await client.get(f"{base_url}/health")

            if health_response.status_code == 200:
                print("✅ Main app health check passed")
                health_data = health_response.json()
                print(f"   Status: {health_data.get('status')}")

                # Check MCP server status
                mcp_servers = health_data.get("mcp_servers", {})
                brave_status = mcp_servers.get("brave_search", False)
                print(
                    f"   Brave Search MCP: {'✅ Active' if brave_status else '❌ Inactive'}",
                )

                return brave_status
            print(f"❌ Main app health check failed: {health_response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Main app connection error: {e}")
        print("   Make sure the main application is running")
        return False


async def test_trends_endpoint():
    """Test the trends endpoint with Brave Search."""
    print("\n📈 Testing Trends Endpoint...")

    base_url = "http://localhost:8000"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Test trends endpoint
            trends_payload = {
                "query": "Python web frameworks 2024",
                "limit": 5,
                "include_hn": True,
                "include_brave": True,
            }

            print(f"🔍 Testing trends endpoint: {base_url}/api/v1/trends")
            trends_response = await client.post(
                f"{base_url}/api/v1/trends",
                json=trends_payload,
            )

            if trends_response.status_code == 200:
                print("✅ Trends endpoint test passed")
                trends_data = trends_response.json()

                total_items = trends_data.get("total_items", 0)
                trends_list = trends_data.get("trends", [])
                print(f"   Total trends found: {total_items}")
                print(f"   Trends returned: {len(trends_list)}")

                # Check for Brave Search results
                brave_results = [
                    t for t in trends_list if t.get("source") == "brave_search"
                ]
                print(f"   Brave Search results: {len(brave_results)}")

                if brave_results:
                    print("   Sample Brave Search result:")
                    sample = brave_results[0]
                    print(f"   - Title: {sample.get('title', 'N/A')[:60]}...")
                    print(f"   - Score: {sample.get('score', 'N/A')}")
                    print(f"   - Source: {sample.get('source', 'N/A')}")

                return len(brave_results) > 0
            print(f"❌ Trends endpoint test failed: {trends_response.status_code}")
            try:
                error_data = trends_response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Response: {trends_response.text[:200]}")
            return False

    except Exception as e:
        print(f"❌ Trends endpoint error: {e}")
        return False


async def main():
    """Run all tests."""
    print("🧪 Brave Search MCP Integration Test Suite")
    print("=" * 50)

    # Check environment
    if not os.getenv("BRAVE_API_KEY"):
        print("❌ BRAVE_API_KEY is not set in environment")
        print("\nTo run this test:")
        print("1. Get a Brave Search API key from: https://brave.com/search/api/")
        print("2. Add it to your .env file: BRAVE_API_KEY=your_key_here")
        print("3. Start the services: ./docker-start.sh")
        print("4. Run this test: python test_brave_integration.py")
        return False

    all_passed = True

    # Test 1: Brave MCP Server
    test1_passed = await test_brave_mcp_server()
    all_passed = all_passed and test1_passed

    # Test 2: Main App Integration
    test2_passed = await test_main_app_integration()
    all_passed = all_passed and test2_passed

    # Test 3: Trends Endpoint (only if previous tests passed)
    if test1_passed and test2_passed:
        test3_passed = await test_trends_endpoint()
        all_passed = all_passed and test3_passed
    else:
        print("\n⏭️  Skipping trends endpoint test due to previous failures")

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Brave Search MCP integration is working correctly.")
    else:
        print("❌ Some tests failed. Please check the logs above.")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
