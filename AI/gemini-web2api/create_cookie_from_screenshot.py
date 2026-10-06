#!/usr/bin/env python3
"""Create cookie.txt from the cookies visible in the screenshots."""

# Based on the screenshots, here are the cookies with their values:
COOKIES = {
    # From screenshot - all .google.com domain cookies
    "SID": "g.a000_Qg-eyPXiJQaHdX9Cz2Qin0rLc5rj5n4XRkn3C4kJLFHo3k_rztyJergbkDBXavGieoJFQACgYKAZISARISFQHGX2MizJ8SIIgfaK8PP1T7pxBSZRoVAUF8yKoae1Y2Yv529Ecex9WEfVMV0076",
    "HSID": "AsSNw_c6nYTD5y-Is",
    "SSID": "AFe2nhcIdhEB6KO9s",
    "APISID": "pmSeMwVH2I1hcbfr-Awmc7bR_PYMuJUYnqA",
    "SAPISID": "v3BfwPNe9rhaxaym/AmuSC_Q2CikRNGgw6",
    "__Secure-1PSID": "g.a000_Qg-eyPXiJQaHdX9Cz2Qin0rLc5rj5n4XRkn3C4kJLFHo3k_DPquFM9kO25mQrt8conSKwACgYKAfMSARISFQHGX2MiVi689PSo5n0HQmeWltSOQhoVAUF8yKqaheH18wOdTjja05pECF6A0076",
    "__Secure-3PSID": "g.a000_Qg-eyPXiJQaHdX9Cz2Qin0rLc5rj5n4XRkn3C4kJLFHo3k_rztyJergbkDBXavGieoJFQACgYKAZISARISFQHGX2MizJ8SIIgfaK8PP1T7pxBSZRoVAUF8yKoae1Y2Yv529Ecex9WEfVMV0076",
    "__Secure-1PAPISID": "v3BfwPNe9rhaxaym/AmuSC_Q2CikRNGgw6",
    "__Secure-3PAPISID": "v3BfwPNe9rhaxaym/AmuSC_Q2CikRNGgw6",
    "__Secure-1PSIDTS": "sidts-CjIBPWEu2W1_Sd7YyD5yVWuc2S4Y5dpse6r7w2zEaRVeHBhVQkHJsMXzLqAyU46bAA",
    "__Secure-3PSIDTS": "sidts-CjIBPWEu2W1_Sd7YyD5yVWuc2S4Y5dpse6r7w2zEaRVeHBhVQkHJsMXzLqAyU46bAA",
    "__Secure-1PSIDCC": "AKEyXzWHvAq8r5bR7zmsScJhegXYM4S2gm0xUg9_dPxH21-4muDzePHoHY_pQBBx",
    "__Secure-3PSIDCC": "AKEyXzWmMbPh-xzTgqs3MYjH3DQLg_kWmzN2nYAZPHDsMyqPqCNLJRc",
    "NID": "533=O0IIR8DlAtMfFaUnh79PYJBPzGFI6NzxWDitofUFo8jug9E6pVnPe0xIGcB9UgHnlpGJ3dR1AE1WQLMgHS6dUlvpO9LN8wYzRQB2_9AfCoUMW8w3K0oY2e2GAy5twEmbuYYNHbULg6fvAiSjZs5lZk45nHZM7OA3vGkZa4...",
    "AEC": "AdJVEauyEKmu6s4S3CzvabWBEsJ27LcCT64OqjabKNpS1PRsF7E70KnjTg",
    "COMPASS": "gemini-pd=CjwACWuJV93jFYb_b6k1ZbZc5AVi75OXfwVJx6huPFdJgLZgT-iphNSBtyIyTho-2Gurv4U86El7hPmdVFUQ5PSA0wYaaAAJa4lXzb2cRTXl9UyjHZ2Nr6aLW1Sq01aOSD_gqlKlP2ZprSks8RC3kAcgEj4robFamDhrN9m...",
}

def create_cookie_file():
    """Create cookie.txt with all required cookies."""
    print("\n" + "="*70)
    print("  Creating cookie.txt from screenshots")
    print("="*70 + "\n")
    
    # Build cookie string
    cookie_parts = []
    for name, value in COOKIES.items():
        cookie_parts.append(f"{name}={value}")
    
    cookie_string = "; ".join(cookie_parts)
    
    # Save to cookie.txt
    with open("cookie.txt", "w", encoding="utf-8") as f:
        f.write(cookie_string)
    
    print(f"✅ Created cookie.txt with {len(COOKIES)} cookies\n")
    
    # Show what we have
    print("📋 Cookies included:")
    for name in COOKIES.keys():
        print(f"   ✓ {name}")
    
    # Check for required cookies
    required = ["SID", "HSID", "SSID", "APISID", "SAPISID", "__Secure-1PSID"]
    missing = [r for r in required if r not in COOKIES]
    
    if missing:
        print(f"\n⚠️  Missing required cookies:")
        for m in missing:
            print(f"   ✗ {m}")
    else:
        print(f"\n✅ All required cookies present!")
    
    print(f"\n📄 Cookie string length: {len(cookie_string)} characters")
    print(f"📄 Preview (first 100 chars): {cookie_string[:100]}...\n")
    
    # Also save as JSON
    import json
    json_data = {
        "cookie": cookie_string,
        "sapisid": COOKIES.get("SAPISID", "")
    }
    
    with open("cookie.json", "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)
    
    print("✅ Also saved as cookie.json\n")
    
    print("="*70)
    print("📝 Next steps:")
    print("="*70)
    print("1. Restart gemini-web2api server:")
    print("   Ctrl+C (stop current server)")
    print("   python -m gemini_web2api.server")
    print("\n2. Test vision:")
    print("   python test_vision_simple.py")
    print("\n3. If successful, test with real image:")
    print("   python test_vision.py your_image.jpg")
    print("="*70 + "\n")


if __name__ == "__main__":
    create_cookie_file()
