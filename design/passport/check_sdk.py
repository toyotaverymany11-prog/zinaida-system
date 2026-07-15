#!/usr/bin/env python3
"""Check replicate SDK version and available methods."""
import replicate
import os

print(f"replicate version: {getattr(replicate, '__version__', 'unknown')}")
print(f"replicate dir: {[x for x in dir(replicate) if not x.startswith('_')]}")

# Check Client
if hasattr(replicate, 'Client'):
    c = replicate.Client(api_token=os.environ.get('REPLICATE_API_TOKEN'))
    print(f"Client dir: {[x for x in dir(c) if not x.startswith('_')]}")

# Check files
if hasattr(replicate, 'files'):
    print(f"files dir: {[x for x in dir(replicate.files) if not x.startswith('_')]}")
else:
    print("No 'files' attribute")

# Check run
if hasattr(replicate, 'run'):
    print("replicate.run exists")
