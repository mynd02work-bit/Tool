#!/usr/bin/env python3
"""Check cookie file status and configuration."""
import os
import json
from pathlib import Path

def check_cookie_file():
    """Check if cookie file exists and is valid."""
    print("\n" + "="*70)
    print("  Cookie Configuration Check")
    print("="*70 + "\n")
    
    # Check cookie.txt
    cookie_file = Path("cookie.txt")
    if cookie_file.exists():
        print("✅ cookie.txt exists")
        size = cookie_file.stat().st_size
        print(f"   Size: {size} bytes")
        
        with open(cookie_file, "r") as f:
            content = f.read().strip()
            
        # Check for important cookies
        required = ["__Secure-1PSID", "SAPISID"]
        found = []
        missing = []
        
        for req in required:
            if req in content:
                found.append(req)
            else:
                missing.append(req)
        
        print(f"\n📋 Cookie validation:")
        for name in found:
            print(f"   ✓ {name} found")
        
        if missing:
            print(f"\n⚠️  Missing cookies:")
            for name in missing:
                print(f"   ✗ {name}")
        
        # Show preview
        print(f"\n📄 Preview (first 80 chars):")
        print(f"   {content[:80]}...")
        
    else:
        print("❌ cookie.txt NOT found")
        print("   Run: python generate_cookie_from_json.py")
    
    print()
    
    # Check config.json
    config_file = Path("config.json")
    if config_file.exists():
        print("✅ config.json exists")
        
        with open(config_file, "r") as f:
            config = json.load(f)
        
        cookie_file_config = config.get("cookie_file")
        if cookie_file_config:
            print(f"   ✓ cookie_file configured: {cookie_file_config}")
        else:
            print("   ✗ cookie_file NOT configured")
            print('   Add: "cookie_file": "cookie.txt"')
        
        print(f"   Port: {config.get('port', 'not set')}")
        print(f"   Model: {config.get('default_model', 'not set')}")
        print(f"   Log requests: {config.get('log_requests', False)}")
        
    else:
        print("❌ config.json NOT found")
    
    print("\n" + "="*70)
    
    # Recommendations
    if cookie_file.exists() and config_file.exists():
        if config.get("cookie_file"):
            print("✅ Configuration looks good!")
            print("\n📝 Next step: Restart server to load new cookies")
            print("   1. Stop current server (Ctrl+C)")
            print("   2. Start: python -m gemini_web2api.server")
            print("   3. Test: python test_vision_simple.py")
        else:
            print("⚠️  Configuration incomplete")
            print("\n📝 Add to config.json:")
            print('   "cookie_file": "cookie.txt"')
    else:
        print("⚠️  Setup incomplete")
        print("\n📝 Run setup:")
        print("   python generate_cookie_from_json.py")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    check_cookie_file()
