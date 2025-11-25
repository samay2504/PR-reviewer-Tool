"""Command-line interface for PR Agent."""

import argparse
import sys
import re
import json
import subprocess
import time
import os
from typing import Optional, Tuple
import requests
from urllib.parse import urlparse

from .utils.github_client import GitHubClient
from .utils.config import settings
from .utils.logging import get_logger

logger = get_logger(__name__)


class PRAgentCLI:
    """Interactive CLI for PR Agent."""
    
    def __init__(self):
        self.github_client = GitHubClient(token=settings.github_token)
        self.api_base_url = "http://localhost:8000"
    
    def parse_github_url(self, url: str) -> Optional[Tuple[str, Optional[int]]]:
        """
        Parse GitHub URL to extract repo and PR number.
        
        Supports formats:
        - https://github.com/owner/repo/pull/123
        - https://github.com/owner/repo
        - owner/repo
        
        Args:
            url: GitHub URL or repo identifier
            
        Returns:
            Tuple of (repo, pr_number) or None if invalid
        """
        # Remove trailing slashes
        url = url.rstrip('/')
        
        # Pattern: https://github.com/owner/repo/pull/123
        pr_pattern = r'github\.com/([^/]+/[^/]+)/pull/(\d+)'
        match = re.search(pr_pattern, url)
        if match:
            repo = match.group(1)
            pr_number = int(match.group(2))
            return (repo, pr_number)
        
        # Pattern: https://github.com/owner/repo
        repo_pattern = r'github\.com/([^/]+/[^/]+)'
        match = re.search(repo_pattern, url)
        if match:
            repo = match.group(1)
            return (repo, None)
        
        # Pattern: owner/repo or owner/repo/pull/123
        if '/' in url:
            parts = url.split('/')
            if len(parts) >= 2:
                repo = f"{parts[0]}/{parts[1]}"
                if len(parts) >= 4 and parts[2] == 'pull':
                    try:
                        pr_number = int(parts[3])
                        return (repo, pr_number)
                    except ValueError:
                        pass
                return (repo, None)
        
        return None
    
    def list_and_select_pr(self, repo: str, state: str = "open") -> Optional[int]:
        """
        List PRs and let user select one.
        
        Args:
            repo: Repository in format "owner/repo"
            state: PR state ("open", "closed", "all")
            
        Returns:
            Selected PR number or None
        """
        print(f"\n🔍 Fetching {state} PRs from {repo}...")
        
        prs = self.github_client.list_pull_requests(repo, state=state, limit=20)
        
        if not prs:
            print(f"❌ No {state} PRs found or failed to fetch.")
            return None
        
        print(f"\n📋 Found {len(prs)} {state} PR(s):\n")
        print(f"{'#':<6} {'Title':<60} {'State':<10} {'Author':<20}")
        print("-" * 100)
        
        for pr in prs:
            number = pr['number']
            title = pr['title'][:57] + "..." if len(pr['title']) > 60 else pr['title']
            state = pr['state']
            author = pr['user']['login']
            print(f"{number:<6} {title:<60} {state:<10} {author:<20}")
        
        print("\n" + "-" * 100)
        
        while True:
            try:
                choice = input("\n🎯 Enter PR number to analyze (or 'q' to quit): ").strip()
                
                if choice.lower() == 'q':
                    return None
                
                pr_number = int(choice)
                
                # Validate PR number exists in list
                if any(pr['number'] == pr_number for pr in prs):
                    return pr_number
                else:
                    print(f"⚠️  PR #{pr_number} not in the list. Please choose from the displayed PRs.")
            
            except ValueError:
                print("⚠️  Invalid input. Please enter a valid PR number or 'q' to quit.")
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted by user.")
                return None
    
    def analyze_pr(self, repo: str, pr_number: int, output_format: str = "json") -> bool:
        """
        Analyze a PR using the API.
        
        Args:
            repo: Repository in format "owner/repo"
            pr_number: Pull request number
            output_format: Output format ("json" or "markdown")
            
        Returns:
            True if successful, False otherwise
        """
        print(f"\n🔬 Analyzing {repo} PR #{pr_number}...")
        print(f"⏳ This may take a few seconds...\n")
        
        try:
            endpoint = "/analyze/markdown" if output_format == "markdown" else "/analyze"
            url = f"{self.api_base_url}{endpoint}"
            
            payload = {
                "repo": repo,
                "pr_number": pr_number
            }
            
            response = requests.post(url, json=payload, timeout=120)
            
            if response.status_code == 200:
                if output_format == "markdown":
                    # Markdown response
                    result = response.json()
                    print("\n" + "=" * 100)
                    print(result.get("markdown", "No markdown output"))
                    print("=" * 100 + "\n")
                else:
                    # JSON response
                    result = response.json()
                    self._print_analysis_result(result)
                
                return True
            else:
                print(f"❌ Analysis failed with status {response.status_code}")
                print(f"Error: {response.text}")
                return False
        
        except requests.exceptions.ConnectionError:
            print("❌ Failed to connect to API server.")
            print("💡 Make sure the server is running: pr-agent server start")
            return False
        except requests.exceptions.Timeout:
            print("❌ Request timed out. The PR might be too large.")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
    
    def _print_analysis_result(self, result: dict):
        """Pretty print analysis result."""
        print("\n" + "=" * 100)
        print(f"📊 Analysis Result for {result.get('repo', 'unknown')}/{result.get('pr_number', '?')}")
        print("=" * 100 + "\n")
        
        summary = result.get('summary', {})
        
        print(f"📁 Files Analyzed: {summary.get('total_files', 0)}")
        print(f"🔍 Issues Found: {summary.get('total_comments', 0)}")
        print(f"🤖 Provider: {result.get('provider', 'unknown')}")
        print(f"💾 From Cache: {'Yes' if result.get('cached', False) else 'No'}")
        
        # Statistics
        stats = summary.get('statistics', {})
        if stats:
            print(f"\n📈 By Severity:")
            severity = stats.get('severity_counts', {})
            print(f"   Critical: {severity.get('critical', 0)}")
            print(f"   High: {severity.get('high', 0)}")
            print(f"   Medium: {severity.get('medium', 0)}")
            print(f"   Low: {severity.get('low', 0)}")
        
        # Executive Summary
        exec_summary = summary.get('executive_summary', '')
        if exec_summary:
            print(f"\n📝 Executive Summary:")
            print("-" * 100)
            print(exec_summary)
            print("-" * 100)
        
        # Recommendation
        recommendation = summary.get('recommendation', '')
        if recommendation:
            rec_emoji = {
                'APPROVE': '✅',
                'APPROVE_WITH_SUGGESTIONS': '⚠️',
                'REQUEST_CHANGES': '🔄',
                'BLOCK_MERGE': '❌'
            }.get(recommendation, '❓')
            
            print(f"\n{rec_emoji} Recommendation: {recommendation.replace('_', ' ').title()}")
        
        print("\n" + "=" * 100 + "\n")
    
    def interactive_mode(self):
        """Run interactive mode for PR analysis."""
        print("\n" + "=" * 100)
        print("🤖 PR Agent - Interactive Mode")
        print("=" * 100)
        print("\nSupported inputs:")
        print("  • GitHub URL: https://github.com/owner/repo/pull/123")
        print("  • Repo URL: https://github.com/owner/repo (will list PRs)")
        print("  • Repo name: owner/repo (will list PRs)")
        print("  • Direct: owner/repo 123 (space-separated)")
        print("  • Type 'q' to quit\n")
        print("=" * 100 + "\n")
        
        while True:
            try:
                user_input = input("🔗 Enter GitHub URL or repo: ").strip()
                
                if not user_input or user_input.lower() == 'q':
                    print("\n👋 Goodbye!")
                    break
                
                # Check if space-separated format (repo pr_number)
                if ' ' in user_input:
                    parts = user_input.split()
                    if len(parts) == 2:
                        try:
                            repo = parts[0]
                            pr_number = int(parts[1])
                            self.analyze_pr(repo, pr_number)
                            continue
                        except ValueError:
                            print("⚠️  Invalid format. Expected: owner/repo PR_NUMBER")
                            continue
                
                # Parse GitHub URL or repo name
                parsed = self.parse_github_url(user_input)
                
                if not parsed:
                    print("⚠️  Invalid input. Please enter a valid GitHub URL or repo name.")
                    continue
                
                repo, pr_number = parsed
                
                # If no PR number, list PRs
                if pr_number is None:
                    pr_number = self.list_and_select_pr(repo)
                    if pr_number is None:
                        continue
                
                # Analyze the PR
                self.analyze_pr(repo, pr_number)
                
                # Ask if user wants to continue
                print()
                continue_choice = input("🔄 Analyze another PR? (y/n): ").strip().lower()
                if continue_choice != 'y':
                    print("\n👋 Goodbye!")
                    break
            
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted by user. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                logger.exception("Error in interactive mode")
    
    def check_server_status(self) -> bool:
        """Check if API server is running."""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def start_server(self, port: int = 8000, host: str = "127.0.0.1"):
        """Start the API server."""
        if self.check_server_status():
            print("✅ Server is already running!")
            return
        
        print(f"🚀 Starting PR Agent server on {host}:{port}...")
        print("💡 Press Ctrl+C to stop the server\n")
        
        try:
            import uvicorn
            from .api.main import app
            
            uvicorn.run(app, host=host, port=port, log_level="info")
        except KeyboardInterrupt:
            print("\n\n🛑 Server stopped by user.")
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            logger.exception("Server startup failed")


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="PR Agent - Automated Pull Request Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (easiest)
  pr-agent

  # Analyze specific PR
  pr-agent analyze facebook/react 31000
  pr-agent analyze https://github.com/django/django/pull/20316

  # List and select PRs
  pr-agent list django/django

  # Server management
  pr-agent server start
  pr-agent server start --port 8080
  pr-agent server status

  # Quick analysis
  pr-agent quick django/django 20316
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Interactive mode (default)
    parser.set_defaults(command='interactive')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a specific PR')
    analyze_parser.add_argument('repo', help='Repository (owner/repo) or GitHub URL')
    analyze_parser.add_argument('pr_number', type=int, nargs='?', help='PR number (optional if in URL)')
    analyze_parser.add_argument('--format', choices=['json', 'markdown'], default='json', help='Output format')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List PRs from a repository')
    list_parser.add_argument('repo', help='Repository (owner/repo) or GitHub URL')
    list_parser.add_argument('--state', choices=['open', 'closed', 'all'], default='open', help='PR state')
    
    # Server command
    server_parser = subparsers.add_parser('server', help='Manage API server')
    server_parser.add_argument('action', choices=['start', 'status'], help='Server action')
    server_parser.add_argument('--port', type=int, default=8000, help='Server port')
    server_parser.add_argument('--host', default='127.0.0.1', help='Server host')
    
    # Quick command (analyze without interactive selection)
    quick_parser = subparsers.add_parser('quick', help='Quick analysis (non-interactive)')
    quick_parser.add_argument('repo', help='Repository (owner/repo)')
    quick_parser.add_argument('pr_number', type=int, help='PR number')
    quick_parser.add_argument('--format', choices=['json', 'markdown'], default='json', help='Output format')
    
    args = parser.parse_args()
    
    cli = PRAgentCLI()
    
    try:
        if args.command == 'interactive' or args.command is None:
            # Interactive mode
            cli.interactive_mode()
        
        elif args.command == 'analyze':
            # Parse repo/URL
            parsed = cli.parse_github_url(args.repo)
            if not parsed:
                print("❌ Invalid repository or URL")
                sys.exit(1)
            
            repo, pr_number_from_url = parsed
            pr_number = args.pr_number or pr_number_from_url
            
            if pr_number is None:
                # No PR number, list PRs
                pr_number = cli.list_and_select_pr(repo)
                if pr_number is None:
                    sys.exit(0)
            
            success = cli.analyze_pr(repo, pr_number, args.format)
            sys.exit(0 if success else 1)
        
        elif args.command == 'list':
            parsed = cli.parse_github_url(args.repo)
            if not parsed:
                print("❌ Invalid repository or URL")
                sys.exit(1)
            
            repo, _ = parsed
            pr_number = cli.list_and_select_pr(repo, args.state)
            
            if pr_number:
                analyze = input("\n🔬 Analyze selected PR? (y/n): ").strip().lower()
                if analyze == 'y':
                    cli.analyze_pr(repo, pr_number)
        
        elif args.command == 'server':
            if args.action == 'start':
                cli.start_server(args.port, args.host)
            elif args.action == 'status':
                if cli.check_server_status():
                    print("✅ Server is running")
                    sys.exit(0)
                else:
                    print("❌ Server is not running")
                    sys.exit(1)
        
        elif args.command == 'quick':
            success = cli.analyze_pr(args.repo, args.pr_number, args.format)
            sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logger.exception("CLI error")
        sys.exit(1)


if __name__ == '__main__':
    main()
