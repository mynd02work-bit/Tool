#!/usr/bin/env python3
"""Update cookie.txt with ALL cookies including SID, HSID, APISID."""
import json

# Your exported cookies
COOKIES_JSON = """
[
    {
        "domain": ".google.com",
        "name": "SAPISID",
        "value": "v3BfwPNe9rhaxaym/AmuSC_Q2CikRNGgw6"
    },
    {
        "domain": ".google.com",
        "name": "__Secure-3PAPISID",
        "value": "v3BfwPNe9rhaxaym/AmuSC_Q2CikRNGgw6"
    },
    {
        "domain": ".google.com",
        "name": "AEC",
        "value": "AdJVEauyEKmu6s4S3CzvabWBEsJ27LcCT64OqjabKNpS1PRsF7E70KnjTg"
    },
    {
        "domain": ".google.com",
        "name": "NID",
        "value": "533=O0IIR8DlAtMfFaUnh79PYJBPzGFI6NzxWDitofUFo8jug9E6pVnPe0xIGcB9UgHnlpGJ3dR1AE1WQLMgHS6dUlvpO9LN8wYzRQB2_9AfCoUMW8w3K0oY2e2GAy5twEmbuYYNHbULg6fvAiSjZs5lZk45nHZM7OA3vGkZa4q2Pjlrkk-B46fUlvvHW62wB3m3lYsmc1SjOUvzlEKVDlqXP_4ttzxy31x-QwYKDDC_2t5ifr6JY8Lqw3_xKfZicRCKExOk-rHbTZ3ejorIeuvX5GjQTt9ldfCH4FWdz8erblsl3YdXxom77CqABRgtmwYo16NDab_0Pqa-d4BkwrMBpd7bFlZocoMYLJlsFOytYzecioktKy5u7ol92759Wh7mGfg0bM162_RRgHP4B-I0t5-2oav8b0eOMHItgF2SPPGkKaRSdCaHzTDRT-XDTGWRtdnB0KumIpWYBfdD79weVVSH22ENcoKeZeFk-hYBEyFqG46zUk9AwJcp1JKWxTMxIxMap6HeTpitCxRN9xYeLYgkgQlBzcmXexU5f_GWOsMrjT2dwVY8ChmeyjkQ26T9kvbdlUB013qw3Df55ci8k53Vsne8wVqTu6GhMZ5n8vlOl1JF74ThYNCrJtTYIXc6ajSjNsB0NVR8JixUe623hMLFf8IQHfYhyP1pYYXBWijScikpvR0MIqp1Os_vn3oB8Y9Yy168eQ1DT8pFnSBK2j65apaEzgIMQTarzzG7oY_TjByb3D709F-DcErH9e3BY0G3YnCpqjD2aeCnhzLBP86-sjJI0Xwu4oEcNpgZXvFY5CBtLj_iAkQJ4x5ePe6wo45Gi_15RqIVRYREJpNaeLNr5EuIa7P7KYn6bqOlHJy-xFa3hO4KzzRwIJ2xtXH0nQRZdqM-1jWbksQNqlzGpIEYYIn3vktpdO_Dc2DuZ77jAGSwILQThaT1UJlSI6ZhPRauz-V6qFCtLF0whxvnWU87auJG-mLaoDdiSeeDBbPIC4fVQ6gjM34YfRof2GTu9me6S6zdhflkqJvyIpKNgi8ZSuZ0dYgYCEg"
    },
    {
        "domain": ".google.com",
        "name": "__Secure-1PSIDTS",
        "value": "sidts-CjIBPWEu2S55f_Fi3zqUBvjLDwpKjMH16THGKtDPjg5dXyrhGxxKFhxGiirJhrzkq5d93hAA"
    },
    {
        "domain": ".google.com",
        "name": "__Secure-1PAPISID",
        "value": "v3BfwPNe9rhaxaym/AmuSC_Q2CikRNGgw6"
    },
    {
        "domain": ".google.com",
        "name": "__Secure-3PSID",
        "value": "g.a000_Qg-eyPXiJQaHdX9Cz2Qin0rLc5rj5n4XRkn3C4kJLFHo3k_rztyJergbkDBXavGieoJFQACgYKAZISARISFQHGX2MizJ8SIIgfaK8PP1T7pxBSZRoVAUF8yKoae1Y2Yv529Ecex9WEfVMV0076"
    },
    {
        "domain": ".google.com",
        "name": "__Secure-1PSID",
        "value": "g.a000_Qg-eyPXiJQaHdX9Cz2Qin0rLc5rj5n4XRkn3C4kJLFHo3k_DPquFM9kO25mQrt8conSKwACgYKAfMSARISFQHGX2MiVi689PSo5n0HQmeWltSOQhoVAUF8yKqaheH18wOdTjja05pECF6A0076"
    },
    {
        "domain": ".google.com",
        "name": "__Secure-1PSIDCC",
        "value": "AKEyXzUNyrNnNQZAo910CAVVDaQ9yVDCDn_cbHPlzxcWzfW0PpScjrR3VpemlvGX3-YznbE3fEs"
    },
    {
        "domain": ".google.com",
        "name": "__Secure-3PSIDCC",
        "value": "AKEyXzUpa3HLY4qk_kGpQqOmALeaduBrIc7_jsm6JBuC6ho_pC4QTGNUjPgffAZs_5EGpa_azXc"
    },
    {
        "domain": ".google.com",
        "name": "__Secure-3PSIDTS",
        "value": "sidts-CjIBPWEu2S55f_Fi3zqUBvjLDwpKjMH16THGKtDPjg5dXyrhGxxKFhxGiirJhrzkq5d93hAA"
    },
    {
        "domain": ".google.com",
        "name": "SSID",
        "value": "AFe2nhcIdhEB6KO9s"
    }
]
"""

# Need to find SID, HSID, APISID from the original export
# These might be missing, let me check the original JSON you provided

print("\n⚠️  IMPORTANT: Your exported cookies are missing SID, HSID, and APISID")
print("These are REQUIRED for Gemini Web API authentication.\n")
print("📝 Please export cookies again and make sure to include:")
print("   - SID")
print("   - HSID") 
print("   - APISID")
print("   - SAPISID (already have)")
print("   - __Secure-1PSID (already have)")
print("\n💡 These cookies should be in the .google.com domain")
print("   Check if they exist in your browser cookies for gemini.google.com\n")

# For now, let's try with anonymous mode (no cookie)
print("="*70)
print("ALTERNATIVE SOLUTION: Use Anonymous Mode")
print("="*70)
print("\nGemini Web2API can work WITHOUT cookies in anonymous mode.")
print("However, this may have limitations:\n")
print("  ✓ Text-only requests work")
print("  ✗ Image upload may not work (needs authentication)")
print("  ✗ Pro model routes to Flash\n")
print("📝 To test anonymous mode:")
print("   1. Rename cookie.txt to cookie.txt.backup")
print("   2. Update config.json: set 'cookie_file' to null")
print("   3. Restart server")
print("   4. Test basic API (should work)")
print("   5. Test vision (may not work)\n")
print("="*70 + "\n")
