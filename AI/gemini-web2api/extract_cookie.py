#!/usr/bin/env python3
"""
Helper script to extract cookies from Chrome/Edge browser for Gemini.
Supports Windows, macOS, and Linux.
"""
import os
import sys
import json
import sqlite3
import shutil
from pathlib import Path
import platform


def get_chrome_cookie_path():
    """Get Chrome cookie database path based on OS."""
    system = platform.system()
    
    if system == "Windows":
        paths = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/User Data/Default/Network/Cookies",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/User Data/Default/Cookies",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/User Data/Default/Network/Cookies",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/User Data/Default/Cookies",
        ]
    elif system == "Darwin":  # macOS
        home = Path.home()
        paths = [
            home / "Library/Application Support/Google/Chrome/Default/Cookies",
            home / "Library/Application Support/Microsoft Edge/Default/Cookies",
        ]
    else:  # Linux
        home = Path.home()
        paths = [
            home / ".config/google-chrome/Default/Cookies",
            home / ".config/chromium/Default/Cookies",
            home / ".config/microsoft-edge/Default/Cookies",
        ]
    
    for path in paths:
        if path.exists():
            return path
    
    return None


def extract_cookies_from_chrome(cookie_db_path):
    """Extract Gemini cookies from Chrome database."""
    # Copy database to temp location (Chrome locks the original)
    temp_db = Path("temp_cookies.db")
    try:
        shutil.copy2(cookie_db_path, temp_db)
    except Exception as e:
        print(f"❌ Error copying cookie database: {e}")
        print(f"💡 Make sure Chrome/Edge is closed and try again")
        return None
    
    try:
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        
        # Query cookies for gemini.google.com
        cursor.execute("""
            SELECT name, value, encrypted_value 
            FROM cookies 
            WHERE host_key LIKE '%google.com%'
            AND (name LIKE '%PSID%' OR name LIKE '%SAPISID%' OR name LIKE '%SID%' OR name = 'HSID' OR name = 'SSID' OR name = 'APISID')
        """)
        
        cookies = {}
        for name, value, encrypted_value in cursor.fetchall():
            if value:
                cookies[name] = value
            elif encrypted_value:
                # Encrypted cookies need decryption (complex, OS-specific)
                # For now, we'll skip and ask user to use manual method
                pass
        
        conn.close()
        temp_db.unlink()
        
        return cookies
        
    except Exception as e:
        print(f"❌ Error reading cookies: {e}")
        if temp_db.exists():
            temp_db.unlink()
        return None


def format_cookie_string(cookies):
    """Format cookies as cookie string."""
    parts = []
    for name, value in cookies.items():
        parts.append(f"{name}={value}")
    return "; ".join(parts)


def save_cookie_file(cookies, output_path="cookie.txt"):
    """Save cookies to file."""
    cookie_str = format_cookie_string(cookies)
    
    # Get SAPISID for JSON format
    sapisid = cookies.get("SAPISID", "")
    
    # Save as simple string format
    with open(output_path, "w") as f:
        f.write(cookie_str)
    
    print(f"✅ Cookies saved to: {output_path}")
    print(f"\n📋 Cookie string:")
    print(f"{cookie_str[:100]}..." if len(cookie_str) > 100 else cookie_str)
    
    # Also save as JSON format
    json_path = output_path.replace(".txt", ".json")
    with open(json_path, "w") as f:
        json.dump({
            "cookie": cookie_str,
            "sapisid": sapisid
        }, f, indent=2)
    
    print(f"\n✅ Also saved as JSON: {json_path}")
    
    return True


def manual_cookie_input():
    """Guide user to manually input cookies."""
    print("\n" + "="*60)
    print("  Manual Cookie Input")
    print("="*60)
    print("\n📖 Instructions:")
    print("1. Open Chrome/Edge and go to: https://gemini.google.com")
    print("2. Press F12 to open DevTools")
    print("3. Go to Application > Cookies > https://gemini.google.com")
    print("4. Copy the values of these cookies:\n")
    
    required_cookies = [
        "__Secure-1PSID",
        "__Secure-1PSIDTS", 
        "SAPISID",
        "HSID",
        "SSID",
        "APISID",
        "SID"
    ]
    
    cookies = {}
    
    for cookie_name in required_cookies:
        value = input(f"\n{cookie_name}: ").strip()
        if value:
            cookies[cookie_name] = value
    
    if not cookies:
        print("\n❌ No cookies entered.")
        return False
    
    # Save to file
    return save_cookie_file(cookies)


def main():
    """Main function."""
    print("\n" + "="*60)
    print("  Gemini Cookie Extractor")
    print("="*60)
    
    print("\n🔍 Searching for Chrome/Edge cookie database...")
    
    cookie_db = get_chrome_cookie_path()
    
    if cookie_db:
        print(f"✅ Found: {cookie_db}\n")
        print("⚠️  Note: Automatic extraction may not work due to encryption.")
        print("   If it fails, use manual method instead.\n")
        
        choice = input("Try automatic extraction? (y/n): ").strip().lower()
        
        if choice == 'y':
            print("\n📦 Extracting cookies...")
            print("💡 Make sure Chrome/Edge is closed!\n")
            
            cookies = extract_cookies_from_chrome(cookie_db)
            
            if cookies and len(cookies) > 0:
                print(f"✅ Found {len(cookies)} cookies\n")
                save_cookie_file(cookies)
                return
            else:
                print("❌ Could not extract cookies automatically.")
                print("   Falling back to manual method...\n")
    else:
        print("❌ Chrome/Edge cookie database not found.\n")
    
    # Fallback to manual input
    manual_cookie_input()
    
    print("\n" + "="*60)
    print("✅ Done!")
    print("="*60)
    print("\n📝 Next steps:")
    print("1. Update config.json to point to cookie.txt:")
    print('   {"cookie_file": "cookie.txt"}')
    print("\n2. Restart gemini-web2api server")
    print("\n3. Test with: python test_vision.py <image_path>\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        sys.exit(0)
