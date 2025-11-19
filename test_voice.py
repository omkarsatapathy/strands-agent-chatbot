#!/usr/bin/env python3
"""Test script for voice generation endpoint."""
import requests
import json

# Test the voice generation endpoint
url = "http://localhost:8000/api/voice/generate"

payload = {
    "text": "Hello, this is a test of the text to speech system.",
    "response_format": "wav"
}

print(f"Testing voice endpoint: {url}")
print(f"Payload: {payload}")

try:
    response = requests.post(url, json=payload)
    print(f"\nResponse status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")

    if response.status_code == 200:
        print(f"Success! Received {len(response.content)} bytes")

        # Save to file
        with open("test_audio.wav", "wb") as f:
            f.write(response.content)
        print("Saved to test_audio.wav")
    else:
        print(f"Error: {response.text}")

except Exception as e:
    print(f"Error: {e}")
