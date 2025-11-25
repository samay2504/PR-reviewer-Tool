"""
Command-line interface for PR Review Agent
Usage: python cli.py analyze --file diff.txt
"""

import argparse
import json
import sys
from pathlib import Path

import requests


DEFAULT_URL = "http://localhost:8000"


def analyze_file(file_path: str, base_url: str = DEFAULT_URL, no_cache: bool = False):
    """Analyze a diff file."""
    try:
        # Read diff file
        diff_text = Path(file_path).read_text(encoding='utf-8')
        
        print(f"📄 Reading diff from: {file_path}")
        print(f"📊 Diff size: {len(diff_text)} bytes")
        print()
        
        # Send to API
        print("🔄 Sending to API for analysis...")
        response = requests.post(
            f"{base_url}/analyze",
            json={
                "diff_text": diff_text,
                "use_cache": not no_cache
            },
            timeout=300
        )
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ Analysis complete!\n")
            print(f"Request ID: {data['request_id']}")
            print(f"Provider: {data['provider']}")
            print(f"Cached: {data['cached']}")
            print()
            
            # Summary
            summary = data['summary']
            print(f"📈 Summary:")
            print(f"   Total Comments: {summary['total_comments']}")
            print(f"   Total Files: {summary['total_files']}")
            print(f"   Agents: {', '.join(summary['agents_run'])}")
            
            if summary.get('fallback_agents'):
                print(f"   ⚠ Fallback agents: {', '.join(summary['fallback_agents'])}")
            print()
            
            # Comments
            if data['comments']:
                print(f"📝 Review Comments ({len(data['comments'])}):")
                print("-" * 80)
                
                for i, comment in enumerate(data['comments'], 1):
                    severity_icon = {
                        "CRITICAL": "🔴",
                        "HIGH": "🟠",
                        "MEDIUM": "🟡",
                        "LOW": "🟢"
                    }.get(comment['severity'], "⚪")
                    
                    print(f"\n{i}. {severity_icon} [{comment['severity']}] {comment['category']}")
                    print(f"   File: {comment['file']}:{comment['line_start']}")
                    print(f"   Agent: {comment['agent']}")
                    print(f"   {comment['message']}")
                    
                    if comment.get('suggestion_patch'):
                        print(f"   💡 Suggestion: {comment['suggestion_patch']}")
                
                print("-" * 80)
            else:
                print("✨ No issues found!")
            
            return 0
            
        else:
            print(f"❌ Analysis failed: {response.status_code}")
            print(response.text)
            return 1
            
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        return 1
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to {base_url}")
        print("   Make sure the service is running")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def health_check(base_url: str = DEFAULT_URL):
    """Check service health."""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Service is healthy\n")
            print(f"Version: {data['version']}")
            print(f"LLM Provider: {data['llm_provider']}")
            print(f"Templates: {data['templates_loaded']}")
            print(f"Cache: {'Redis' if data['redis_available'] else 'Disk (fallback)'}")
            return 0
        else:
            print(f"⚠ Service returned: {response.status_code}")
            return 1
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to {base_url}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def list_templates(base_url: str = DEFAULT_URL):
    """List available templates."""
    try:
        response = requests.get(f"{base_url}/templates", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            templates = data['templates']
            
            print(f"📋 Available Templates ({len(templates)}):\n")
            
            for template in templates:
                print(f"• {template['id']} (v{template['version']})")
                print(f"  {template['description']}")
                print(f"  Variables: {', '.join(v['name'] for v in template['variables'])}")
                print()
            
            return 0
        else:
            print(f"❌ Failed: {response.status_code}")
            return 1
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="PR Review Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a diff file
  python cli.py analyze --file my_diff.txt
  
  # Check service health
  python cli.py health
  
  # List templates
  python cli.py templates
  
  # Use custom URL
  python cli.py analyze --file diff.txt --url http://example.com:8000
        """
    )
    
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Base URL of PR Review Agent (default: {DEFAULT_URL})"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a diff file")
    analyze_parser.add_argument(
        "--file", "-f",
        required=True,
        help="Path to diff file"
    )
    analyze_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable cache for this request"
    )
    
    # Health command
    subparsers.add_parser("health", help="Check service health")
    
    # Templates command
    subparsers.add_parser("templates", help="List available templates")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    if args.command == "analyze":
        return analyze_file(args.file, args.url, args.no_cache)
    elif args.command == "health":
        return health_check(args.url)
    elif args.command == "templates":
        return list_templates(args.url)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
