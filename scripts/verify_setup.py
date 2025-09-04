#!/usr/bin/env python3
"""Setup verification script for HN GitHub Agents
Verifies that all components are properly configured and running
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


class SetupVerifier:
    """Verifies the complete setup of HN GitHub Agents."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results: dict[str, bool] = {}
        self.errors: list[str] = []

    def verify_file_exists(self, file_path: str) -> bool:
        """Verify a file exists."""
        path = self.project_root / file_path
        exists = path.exists()
        if not exists:
            self.errors.append(f"Missing file: {file_path}")
        return exists

    def verify_directory_exists(self, dir_path: str) -> bool:
        """Verify a directory exists."""
        path = self.project_root / dir_path
        exists = path.exists() and path.is_dir()
        if not exists:
            self.errors.append(f"Missing directory: {dir_path}")
        return exists

    def verify_python_packages(self) -> bool:
        """Verify required Python packages are installed."""
        required_packages = [
            "fastapi",
            "uvicorn",
            "pydantic",
            "pydantic-ai",
            "httpx",
            "structlog",
            "rich",
        ]

        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            self.errors.append(f"Missing packages: {', '.join(missing_packages)}")
            return False
        return True

    def verify_environment_file(self) -> bool:
        """Verify environment file exists and has required variables."""
        env_file = self.project_root / ".env"
        if not env_file.exists():
            self.errors.append(
                "Missing .env file. Copy from env.example and configure.",
            )
            return False

        required_vars = ["OPENAI_API_KEY"]
        env_content = env_file.read_text()

        missing_vars = []
        for var in required_vars:
            if f"{var}=" not in env_content or f"{var}=your_" in env_content:
                missing_vars.append(var)

        if missing_vars:
            self.errors.append(
                f"Missing/unconfigured environment variables: {', '.join(missing_vars)}",
            )
            return False
        return True

    async def verify_docker_services(self) -> bool:
        """Verify Docker services are running."""
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                check=True,
            )

            running_containers = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    container = json.loads(line)
                    running_containers.append(container.get("Names", ""))

            expected_containers = [
                "brave-search-mcp",
                "github-mcp",
                "hackernews-mcp",
                "filesystem-mcp",
            ]

            missing_containers = [
                name for name in expected_containers if name not in running_containers
            ]

            if missing_containers:
                self.errors.append(
                    f"Missing Docker containers: {', '.join(missing_containers)}. "
                    "Run ./scripts/setup_mcp_servers.sh setup",
                )
                return False
            return True

        except (subprocess.CalledProcessError, FileNotFoundError):
            self.errors.append("Docker not available or not running")
            return False

    async def verify_mcp_servers(self) -> bool:
        """Verify MCP servers are responding."""
        mcp_servers = {
            "Brave Search": "http://localhost:3001",
            "GitHub": "http://localhost:3002",
            "Hacker News": "http://localhost:3003",
            "Filesystem": "http://localhost:3004",
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            all_healthy = True
            for name, url in mcp_servers.items():
                try:
                    response = await client.get(f"{url}/health")
                    if response.status_code != 200:
                        self.errors.append(f"{name} MCP server not healthy at {url}")
                        all_healthy = False
                except httpx.RequestError:
                    self.errors.append(f"{name} MCP server not responding at {url}")
                    all_healthy = False

        return all_healthy

    async def verify_main_application(self) -> bool:
        """Verify the main application starts and responds."""
        try:
            # Try to import the main module
            import app.main

            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.get("http://localhost:8000/health")
                    if response.status_code == 200:
                        return True
                    self.errors.append(
                        f"Application health check failed: {response.status_code}",
                    )
                    return False
                except httpx.RequestError:
                    self.errors.append(
                        "Application not responding. Start with: python -m app.main",
                    )
                    return False

        except ImportError as e:
            self.errors.append(f"Cannot import main application: {e}")
            return False

    def verify_project_structure(self) -> bool:
        """Verify project structure is correct."""
        required_files = [
            "pyproject.toml",
            "docker-compose.yml",
            "Dockerfile",
            "README.md",
            "app/__init__.py",
            "app/main.py",
            "scripts/setup_mcp_servers.sh",
        ]

        required_dirs = [
            "app/agents",
            "app/models",
            "app/services",
            "app/utils",
            "data/examples",
            "data/config",
            "tests",
        ]

        files_ok = all(self.verify_file_exists(f) for f in required_files)
        dirs_ok = all(self.verify_directory_exists(d) for d in required_dirs)

        return files_ok and dirs_ok

    async def run_verification(self) -> bool:
        """Run all verification checks."""
        checks = [
            ("Project Structure", self.verify_project_structure),
            ("Python Packages", self.verify_python_packages),
            ("Environment File", self.verify_environment_file),
            ("Docker Services", self.verify_docker_services),
            ("MCP Servers", self.verify_mcp_servers),
            ("Main Application", self.verify_main_application),
        ]

        console.print("\n[bold blue]🔍 Verifying HN GitHub Agents Setup[/bold blue]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for check_name, check_func in checks:
                task = progress.add_task(f"Checking {check_name}...", total=None)

                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()

                self.results[check_name] = result
                progress.update(task, completed=True)

        return all(self.results.values())

    def print_results(self):
        """Print verification results."""
        table = Table(title="Setup Verification Results")
        table.add_column("Check", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")

        for check_name, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            style = "green" if result else "red"
            table.add_row(check_name, f"[{style}]{status}[/{style}]", "")

        console.print(table)

        if self.errors:
            console.print("\n[bold red]Issues Found:[/bold red]")
            for error in self.errors:
                console.print(f"  • {error}")
        else:
            console.print(
                Panel(
                    "[bold green]🎉 All checks passed! Your setup is ready for the PyCon demo.[/bold green]",
                    border_style="green",
                ),
            )

    def print_next_steps(self):
        """Print next steps based on verification results."""
        if all(self.results.values()):
            console.print(
                Panel(
                    """[bold green]🚀 Ready to Demo![/bold green]

Next steps:
1. Start the application: [cyan]python -m app.main[/cyan]
2. Visit the API docs: [cyan]http://localhost:8000/docs[/cyan]
3. Try the demo endpoints in your PyCon presentation!

[dim]Pro tip: Use the /api/v1/combined-analysis endpoint for the most impressive demo![/dim]""",
                    border_style="green",
                    title="Setup Complete",
                ),
            )
        else:
            console.print(
                Panel(
                    """[bold yellow]⚠️  Setup Issues Detected[/bold yellow]

Please fix the issues above, then run this script again:
[cyan]python scripts/verify_setup.py[/cyan]

Common fixes:
• Install dependencies: [cyan]pip install -e .[/cyan]
• Setup MCP servers: [cyan]./scripts/setup_mcp_servers.sh setup[/cyan]
• Configure environment: [cyan]cp env.example .env[/cyan] and edit""",
                    border_style="yellow",
                    title="Action Required",
                ),
            )


async def main():
    """Main verification function."""
    verifier = SetupVerifier()

    try:
        success = await verifier.run_verification()
        verifier.print_results()
        verifier.print_next_steps()

        return 0 if success else 1

    except KeyboardInterrupt:
        console.print("\n[yellow]Verification cancelled by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[red]Verification failed with error: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
