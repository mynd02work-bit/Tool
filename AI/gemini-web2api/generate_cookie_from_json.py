#!/usr/bin/env python3
"""
Generate cookie.txt from exported JSON cookies.
Usage: python generate_cookie_from_json.py
"""
import json

# Paste your exported cookies JSON here
COOKIES_JSON = """
[
    {
        "domain": ".google.com",
        "expirationDate": 1816756139.618746,
        "hostOnly": false,
        "httpOnly": false,
        "name": "SAPISID",
        "path": "/",
        "sameSite": null,
        "secure": true,
        "session": false,
        "storeId": null,
        "value": "v3BfwPNe9rhaxaym/AmuSC_Q2CikRNGgw6"
    },
    {
        "domain": ".google.com",
        "expirationDate": 1816756139.618781,
        "hostOnly": false,
        "httpOnly": false,
        "name": "__Secure-3PAPISID",
        "path": "/",
        "sameSite": "no_restriction",
        "secure": true,
        "session": false,
        "storeId": null,
        "value": "v3BfwPNe9rhaxaym/AmuSC_Q2CikRNGgw6"
    },
    {
        "domain": ".google.com",
        "expirationDate": 1788840963.58995,
        "hostOnly": false,
        "httpOnly": true,
        "name": "AEC",
        "path": "/",
        "sameSite": "lax",
        "secure": true,
        "session": false,
        "storeId": null,
        "value": "AdJVEauyEKmu6s4S3CzvabWBEsJ27LcCT64OqjabKNpS1PRsF7E70KnjTg"
    },
    {
        "domain": ".google.com",
        "expirationDate": 1800365210.833471,
        "hostOnly": false,
        "httpOnly": true,
        "name": "NID",
        "path": "/",
        "sameSite": "no_restriction",
        "secure": true,
        "session": false,
        "storeId": null,
        "value": "533=O0IIR8DlAtMfFaUnh79PYJBPzGFI6NzxWDitofUFo8jug9E6pVnPe0xIGcB9UgHnlpGJ3dR1AE1WQLMgHS6dUlvpO9LN8wYzRQB2_9AfCoUMW8w3K0oY2e2GAy5twEmbuYYNHbULg6fvAiSjZs5lZk45nHZM7OA3vGkZa4q2Pjlrkk-B46fUlvvHW62wB3m3lYsmc1SjOUvzlEKVDlqXP_4ttzxy31x-QwYKDDC_2t5ifr6JY8Lqw3_xKfZicRCKExOk-rHbTZ3ejorIeuvX5GjQTt9ldfCH4FWdz8erblsl3YdXxom77CqABRgtmwYo16NDab_0Pqa-d4BkwrMBpd7bFlZocoMYLJlsFOytYzecioktKy5u7ol92759Wh7mGfg0bM162_RRgHP4B-I0t5-2oav8b0eOMHItgF2SPPGkKaRSdCaHzTDRT-XDTGWRtdnB0KumIpWYBfdD79weVVSH22ENcoKeZeFk-hYBEyFqG46zUk9AwJcp1JKWxTMxIxMap6HeTpitCxRN9xYeLYgkgQlBzcmXexU5f_GWOsMrjT2dwVY8ChmeyjkQ26T9kvbdlUB013qw3Df55ci8k53Vsne8wVqTu6GhMZ5n8vlOl1JF74ThYNCrJtTYIXc6ajSjNsB0NVR8JixUe623hMLFf8IQHfYhyP1pYYXBWijScikpvR0MIqp1Os_vn3oB8Y9Yy168eQ1DT8pFnSBK2j65apaEzgIMQTarzzG7oY_TjByb3D709F-DcErH9e3BY0G3YnCpqjD2aeCnhzLBP86-sjJI0Xwu4oEcNpgZXvFY5CBtLj_iAkQJ4x5ePe6wo45Gi_15RqIVRYREJpNaeLNr5EuIa7P7KYn6bqOlHJy-xFa3hO4KzzRwIJ2xtXH0nQRZdqM-1jWbksQNqlzGpIEYYIn3vktpdO_Dc2DuZ77jAGSwILQThaT1UJlSI6ZhPRauz-V6qFCtLF0whxvnWU87auJG-mLaoDdiSeeDBbPIC4fVQ6gjM34YfRof2GTu9me6S6zdhflkqJvyIpKNgi8ZSuZ0dYgYCEg"
    },
    {
        "domain": ".google.com",
        "expirationDate": 1816140892.25265,
        "hostOnly": false,
        "httpOnly": true,
        "name": "__Secure-1PSIDTS",
        "path": "/",
        "sameSite": null,
        "secure": true,
        "session": false,
        "storeId": null,
        "value": "sidts-CjIBPWEu2S55f_Fi3zqUBvjLDwpKjMH16THGKtDPjg5dXyrhGxxKFhxGiirJhrzkq5d93hAA"
    },
    {
        "domain": ".gemini.google.com",
        "expirationDate": 1785468900.131864,
        "hostOnly": false,
        "httpOnly": true,
        "name": "COMPASS",
        "path": "/",
        "sameSite": "no_restriction",
        "secure": true,
        "session": false,
        "storeId": null,
        "value": "gemini-pd=CjwACWuJV93jFYb_b6k1ZbZc5AVi75OXfwVJx6huPFdJgLZgT-iphNSBtyIyTho-2Gurv4U86El7hPmdVFUQ5PSA0wYaaAAJa4lXzb2cRTXl9UyjHZ2Nr6aLW1Sq01aOSD_gqlKlP2ZprSks8RC3kAcgEj4robFamDhrN9m2FP4NMQe-tNagMUezUwqGCP-D0EYPBFLvvBT14SPlzMqzO9vxbD7MrhKywglDx0vMIAEwAQ:gemini-hl=CkkACWuJV4Jq7gXnYGXm-CCWRGf1MNczIJ0yMsen8R98zb0fdd_v1HDcw_-Y0Gxw7WZu_GGVl89NUAGecp6EG6tM_DjudIlkdiK-EIe06dIGGnUACWuJVzTWwfjPMwbZhUacqLZR-JqZKgYuzIkBt0XpNTTsGb1snxQDmBYePi0WTBZcqAUiJ-Ii6528i88U8vSUnbouvdmGQfGXWmjay9lHJyrpGxzWI5ADxqGCrEN655-Y6RBGLilExGzba1WBZTwolglTaUcgATAB"
    },
    {
        "domain": ".google.com",
        "expirationDate": 1816756139.618763,
        "hostOnly": false,
        "httpOnly": false,
        "name": "__Secure-1PAPISID",
        "path": "/",
        "sameSite": null,
        "secure": true,
        "session": false,
        "storeId": null,
        "value": "v3BfwPNe9rhaxaym/AmuSC_Q2CikRNGgw6"
    },
    {
        "domain": ".google.com",
        "expirationDate": 1816756139.61861,
        "hostOnly": false,
        "httpOnly": true,
        "name": "__Secure-3PSID",
        "path": "/",
        "sameSite": "no_restriction",
        "secure": true,
        "session": false,
        "storeId": null,
        "value": "g.a000_Qg-eyPXiJQaHdX9Cz2Qin0rLc5rj5n4XRkn3C4kJLFHo3k_rztyJergbkDBXavGieoJFQACgYKAZISARISFQHGX2MizJ8SIIgfaK8PP1T7pxBSZRoVAUF8yKoae1Y2Yv529Ecex9WEfVMV0076"
    },
    {
        "domain": ".google.com",
        "expirationDate": 1816756139.618592,
        "hostOnly": false,
        "httpOnly": true,
        "name": "__Secure-1PSID",
        "path": "/",
        "sameSite": null,
        "secure": true,
        "session": false,
        "storeId": null,
        "value": "g.a000_Qg-eyPXiJQaHdX9Cz2Qin0rLc5rj5n4XRkn3C4kJLFHo3k_DPquFM9kO25mQrt8conSKwACgYKAfMSARISFQHGX2MiVi689PSo5n0HQmeWltSOQhoVAUF8yKqaheH18wOdTjja05pECF6A0076"
    },
    {
        "domain": ".google.com",
        "expirationDate": 1816140929.427169,
        "hostOnly": false,
        "httpOnly": true,
        "name": "__Secure-1PSIDCC",
        "path": "/",
        "sameSite": null,
        "secure": true,
        "session": false,
        "storeId": null,
        "value": "AKEyXzUNyrNnNQZAo910CAVVDaQ9yVDCDn_cbHPlzxcWzfW0PpScjrR3VpemlvGX3-YznbE3fEs"
    },
    {
        "domain": ".google.com",
        "expirationDate": 1816140929.427282,
        "hostOnly": false,
        "httpOnly": true,
        "name": "__Secure-3PSIDCC",
        "path": "/",
        "sameSite": "no_restriction",
        "secure": true,
        "session": false,
        "storeId": null,
        "value": "AKEyXzUpa3HLY4qk_kGpQqOmALeaduBrIc7_jsm6JBuC6ho_pC4QTGNUjPgffAZs_5EGpa_azXc"
    },
    {
        "domain": ".google.com",
        "expirationDate": 1816140892.252848,
        "hostOnly": false,
        "httpOnly": true,
        "name": "__Secure-3PSIDTS",
        "path": "/",
        "sameSite": "no_restriction",
        "secure": true,
        "session": false,
        "storeId": null,
        "value": "sidts-CjIBPWEu2S55f_Fi3zqUBvjLDwpKjMH16THGKtDPjg5dXyrhGxxKFhxGiirJhrzkq5d93hAA"
    },
    {
        "domain": ".google.com",
        "expirationDate": 1788840281.501998,
        "hostOnly": false,
        "httpOnly": true,
        "name": "__Secure-BUCKET",
        "path": "/",
        "sameSite": null,
        "secure": true,
        "session": false,
        "storeId": null,
        "value": "CNED"
    },
    {
        "domain": ".google.com",
        "expirationDate": 1816756139.618712,
        "hostOnly": false,
        "httpOnly": true,
        "name": "SSID",
        "path": "/",
        "sameSite": null,
        "secure": true,
        "session": false,
        "storeId": null,
        "value": "AFe2nhcIdhEB6KO9s"
    }
]
"""

def main():
    print("\n" + "="*70)
    print("  Cookie Generator for Gemini Web2API")
    print("="*70 + "\n")
    
    # Parse JSON
    try:
        cookies = json.loads(COOKIES_JSON)
        print(f"✅ Parsed {len(cookies)} cookies from JSON\n")
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON: {e}")
        return
    
    # Extract important cookies
    important_cookies = [
        "__Secure-1PSID",
        "__Secure-1PSIDTS",
        "SAPISID",
        "SSID",
        "__Secure-1PAPISID",
        "__Secure-3PSID",
        "__Secure-3PAPISID",
        "__Secure-1PSIDCC",
        "__Secure-3PSIDCC",
        "__Secure-3PSIDTS"
    ]
    
    cookie_dict = {}
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        if name and value:
            cookie_dict[name] = value
    
    # Build cookie string
    cookie_parts = []
    found_cookies = []
    
    for name in important_cookies:
        if name in cookie_dict:
            cookie_parts.append(f"{name}={cookie_dict[name]}")
            found_cookies.append(name)
    
    cookie_string = "; ".join(cookie_parts)
    
    print("📋 Found cookies:")
    for name in found_cookies:
        print(f"   ✓ {name}")
    
    if "__Secure-1PSID" not in found_cookies:
        print("\n⚠️  WARNING: Missing __Secure-1PSID (critical for authentication)")
    if "SAPISID" not in found_cookies:
        print("⚠️  WARNING: Missing SAPISID (required for image upload)")
    
    # Save to cookie.txt
    output_file = "cookie.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(cookie_string)
    
    print(f"\n✅ Cookie string saved to: {output_file}")
    print(f"   Length: {len(cookie_string)} characters")
    
    # Also save as JSON format
    json_output = {
        "cookie": cookie_string,
        "sapisid": cookie_dict.get("SAPISID", "")
    }
    
    json_file = "cookie.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2)
    
    print(f"✅ Also saved as JSON: {json_file}\n")
    
    # Show preview
    print("─" * 70)
    print("Preview (first 100 chars):")
    print("─" * 70)
    print(cookie_string[:100] + "..." if len(cookie_string) > 100 else cookie_string)
    print("─" * 70)
    
    print("\n📝 Next steps:")
    print("   1. Update config.json:")
    print('      {"cookie_file": "cookie.txt"}')
    print("\n   2. Restart gemini-web2api server:")
    print("      python -m gemini_web2api.server")
    print("\n   3. Test vision:")
    print("      python test_vision.py test.jpg\n")
    
    print("="*70)
    print("✅ Done!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
