#!/usr/bin/env python3
import asyncio
import aiohttp
import json

# Test edilecek API keyler
API_KEYS = {
    "Claude (Anthropic)": {
        "key": "sk-ant-api03-AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz1234567890",
        "url": "https://api.anthropic.com/v1/messages",
        "test": "anthropic"
    },
    "Llama (OpenRouter)": {
        "key": "sk-or-v1-4f8b9c8d7e6a5f4g3h2i1j0k9l8m7n6o5p4q3r2s1t0u",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "test": "openrouter",
        "model": "meta-llama/llama-3.1-70b-instruct"
    },
    "Dolphin (OpenRouter)": {
        "key": "sk-or-v1-9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "test": "openrouter",
        "model": "cognitivecomputations/dolphin-2.9-llama3-70b"
    },
    "Mixtral (OpenRouter)": {
        "key": "sk-or-v1-2z3y4x5w6v7u8t9s0r1q2p3o4n5m6l7k8j9i0h1g2f3e4d5c",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "test": "openrouter",
        "model": "mistralai/mixtral-8x7b-instruct"
    },
    "Grok": {
        "key": "gsk_7X9vP2mK8nL5qR3tY6uJ9wZ2aS4dF6gH8jK0lM2nP4qR6tY8u",
        "url": "https://api.x.ai/v1/chat/completions",
        "test": "xai"
    }
}

async def test_anthropic(key, url):
    """Test Claude API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 50,
                    "messages": [{"role": "user", "content": "Test"}]
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                status = response.status
                text = await response.text()
                return status, text
    except Exception as e:
        return None, str(e)

async def test_openrouter(key, url, model):
    """Test OpenRouter API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://wormdemon.vercel.app",
                    "X-Title": "x-69 Wormdemon"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Test"}],
                    "max_tokens": 50
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                status = response.status
                text = await response.text()
                return status, text
    except Exception as e:
        return None, str(e)

async def test_xai(key, url):
    """Test xAI (Grok) API"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "grok-beta",
                    "messages": [{"role": "user", "content": "Test"}],
                    "max_tokens": 50
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                status = response.status
                text = await response.text()
                return status, text
    except Exception as e:
        return None, str(e)

async def test_all_keys():
    """Test all API keys"""
    print("=" * 70)
    print("🔥 API KEY TEST BAŞLIYOR")
    print("=" * 70)
    print()
    
    results = {}
    
    for name, config in API_KEYS.items():
        print(f"Testing {name}...")
        
        if config["test"] == "anthropic":
            status, response = await test_anthropic(config["key"], config["url"])
        elif config["test"] == "openrouter":
            status, response = await test_openrouter(config["key"], config["url"], config["model"])
        elif config["test"] == "xai":
            status, response = await test_xai(config["key"], config["url"])
        else:
            status, response = None, "Unknown test type"
        
        if status == 200:
            print(f"  ✅ ÇALIŞIYOR! (Status: {status})")
            results[name] = "WORKING"
        elif status == 401:
            print(f"  ❌ HATALI KEY! (Status: 401 - Unauthorized)")
            results[name] = "INVALID_KEY"
        elif status == 402:
            print(f"  ⚠️  ÖDEME GEREKLİ! (Status: 402 - Payment Required)")
            results[name] = "PAYMENT_REQUIRED"
        elif status == 429:
            print(f"  ⏸️  RATE LIMIT! (Status: 429 - Too Many Requests)")
            results[name] = "RATE_LIMITED"
        elif status is None:
            print(f"  💀 BAĞLANTI HATASI: {response[:100]}")
            results[name] = "CONNECTION_ERROR"
        else:
            print(f"  ⚠️  HATA! (Status: {status})")
            print(f"     Response: {response[:200]}")
            results[name] = f"ERROR_{status}"
        
        print()
        await asyncio.sleep(1)  # Rate limit için bekle
    
    print("=" * 70)
    print("📊 ÖZET SONUÇLAR")
    print("=" * 70)
    print()
    
    working = [k for k, v in results.items() if v == "WORKING"]
    invalid = [k for k, v in results.items() if v == "INVALID_KEY"]
    other = {k: v for k, v in results.items() if v not in ["WORKING", "INVALID_KEY"]}
    
    if working:
        print("✅ ÇALIŞAN API'LER:")
        for api in working:
            print(f"   - {api}")
        print()
    
    if invalid:
        print("❌ HATALI KEYLER:")
        for api in invalid:
            print(f"   - {api}")
        print()
    
    if other:
        print("⚠️  DİĞER DURUMLAR:")
        for api, status in other.items():
            print(f"   - {api}: {status}")
        print()
    
    print("=" * 70)
    print()
    
    # Backend için öneriler
    if working:
        print("💡 BACKEND İÇİN ÖNERİLER:")
        print()
        for api in working:
            if "Claude" in api:
                print(f"   export ANTHROPIC_API_KEY='{API_KEYS[api]['key']}'")
            elif "Llama" in api:
                print(f"   export OPENROUTER_API_KEY_LLAMA='{API_KEYS[api]['key']}'")
            elif "Dolphin" in api:
                print(f"   export OPENROUTER_API_KEY_DOLPHIN='{API_KEYS[api]['key']}'")
            elif "Mixtral" in api:
                print(f"   export OPENROUTER_API_KEY_MIXTRAL='{API_KEYS[api]['key']}'")
            elif "Grok" in api:
                print(f"   export XAI_API_KEY='{API_KEYS[api]['key']}'")
        print()
    
    return results

if __name__ == "__main__":
    asyncio.run(test_all_keys())
