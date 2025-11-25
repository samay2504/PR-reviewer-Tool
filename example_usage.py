"""
Example usage of PR Review Agent
"""

import requests
import json

# Base URL
BASE_URL = "http://localhost:8000"

# Sample diff to analyze
SAMPLE_DIFF = """diff --git a/src/user_service.py b/src/user_service.py
index 1234567..abcdefg 100644
--- a/src/user_service.py
+++ b/src/user_service.py
@@ -1,10 +1,15 @@
 import sqlite3
+import os
 
 def get_user(user_id):
-    conn = sqlite3.connect('database.db')
+    # Hardcoded database credentials - security risk!
+    db_password = "admin123"
+    
+    conn = sqlite3.connect('database.db')
     cursor = conn.cursor()
-    query = f"SELECT * FROM users WHERE id = {user_id}"
+    # SQL injection vulnerability!
+    query = f"SELECT * FROM users WHERE id = {user_id}"
     cursor.execute(query)
+    
     result = cursor.fetchone()
     conn.close()
     return result
"""


def check_health():
    """Check if the service is healthy."""
    print("🔍 Checking service health...")
    response = requests.get(f"{BASE_URL}/health")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Service is healthy!")
        print(f"   Provider: {data['llm_provider']}")
        print(f"   Templates: {data['templates_loaded']}")
        print(f"   Redis: {'Yes' if data['redis_available'] else 'No (using fallback)'}")
    else:
        print(f"❌ Service unhealthy: {response.status_code}")
    
    print()


def analyze_diff():
    """Analyze a sample diff."""
    print("🔍 Analyzing sample diff...")
    print(f"Diff preview: {SAMPLE_DIFF[:100]}...")
    print()
    
    response = requests.post(
        f"{BASE_URL}/analyze",
        json={
            "diff_text": SAMPLE_DIFF,
            "use_cache": False
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Analysis complete!")
        print(f"   Request ID: {data['request_id']}")
        print(f"   Provider: {data['provider']}")
        print(f"   Comments: {data['summary']['total_comments']}")
        print(f"   Agents: {', '.join(data['summary']['agents_run'])}")
        print()
        
        # Display comments
        if data['comments']:
            print("📝 Review Comments:")
            for i, comment in enumerate(data['comments'], 1):
                print(f"\n   {i}. [{comment['severity']}] {comment['category']} - Line {comment['line_start']}")
                print(f"      File: {comment['file']}")
                print(f"      Agent: {comment['agent']}")
                print(f"      Message: {comment['message']}")
                if comment.get('suggestion_patch'):
                    print(f"      Suggestion: {comment['suggestion_patch']}")
        else:
            print("   No issues found!")
        
        return data
    else:
        print(f"❌ Analysis failed: {response.status_code}")
        print(f"   {response.text}")
    
    print()


def list_templates():
    """List available templates."""
    print("📋 Available templates:")
    response = requests.get(f"{BASE_URL}/templates")
    
    if response.status_code == 200:
        data = response.json()
        for template in data['templates']:
            print(f"   - {template['id']} (v{template['version']})")
            print(f"     {template['description']}")
    else:
        print(f"❌ Failed to list templates: {response.status_code}")
    
    print()


def get_stats():
    """Get system statistics."""
    print("📊 System statistics:")
    response = requests.get(f"{BASE_URL}/stats")
    
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
    else:
        print(f"❌ Failed to get stats: {response.status_code}")
    
    print()


def main():
    """Run example usage."""
    print("=" * 60)
    print("PR Review Agent - Example Usage")
    print("=" * 60)
    print()
    
    try:
        # 1. Check health
        check_health()
        
        # 2. List templates
        list_templates()
        
        # 3. Analyze diff
        result = analyze_diff()
        
        # 4. Get stats
        get_stats()
        
        print("=" * 60)
        print("✅ Example completed successfully!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the service!")
        print("   Make sure the service is running: python -m pr_agent.api.main")
        print("   Or use Docker: docker-compose up")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
