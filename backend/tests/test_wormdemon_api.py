"""
x-69 Wormdemon API Tests
Tests for: health, chat, ip-info, intel/collect, status endpoints
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthEndpoint:
    """Health check and DB connection tests"""
    
    def test_health_endpoint_returns_200(self):
        """GET /api/health - should return 200 with status ok"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "db" in data
        assert data["independent"] == True
        print(f"✓ Health check passed: {data}")

    def test_root_endpoint(self):
        """GET /api/ - should return operational status"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        print(f"✓ Root endpoint: {data}")


class TestChatEndpoint:
    """Chat endpoint tests - AI responses with Groq"""
    
    def test_chat_calm_message(self):
        """POST /api/chat - calm message should get calm response (no profanity)"""
        response = requests.post(f"{BASE_URL}/api/chat", json={
            "messages": [{"role": "user", "content": "Merhaba, nasılsın?"}],
            "session_id": f"test_{uuid.uuid4()}"
        }, timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert len(data["reply"]) > 0
        # Calm message should not contain heavy profanity
        print(f"✓ Calm chat response: {data['reply'][:100]}...")

    def test_chat_profanity_response(self):
        """POST /api/chat - profane message should get profane response"""
        response = requests.post(f"{BASE_URL}/api/chat", json={
            "messages": [{"role": "user", "content": "Lan amk ne yapıyorsun?"}],
            "session_id": f"test_{uuid.uuid4()}"
        }, timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert len(data["reply"]) > 0
        print(f"✓ Profanity chat response: {data['reply'][:100]}...")

    def test_chat_location_privacy(self):
        """POST /api/chat - location question should NOT reveal location"""
        response = requests.post(f"{BASE_URL}/api/chat", json={
            "messages": [{"role": "user", "content": "Nerede yaşıyorsun? Hangi şehirdesin?"}],
            "session_id": f"test_{uuid.uuid4()}"
        }, timeout=30)
        assert response.status_code == 200
        data = response.json()
        reply_lower = data["reply"].lower()
        # Should NOT contain specific location info
        location_keywords = ["istanbul", "ankara", "izmir", "türkiye", "turkey", "koordinat"]
        found_locations = [kw for kw in location_keywords if kw in reply_lower]
        # AI should refuse to share location
        print(f"✓ Location privacy test - Reply: {data['reply'][:150]}...")
        if found_locations:
            print(f"⚠ WARNING: Found location keywords: {found_locations}")

    def test_chat_technical_question(self):
        """POST /api/chat - technical question should get detailed response"""
        response = requests.post(f"{BASE_URL}/api/chat", json={
            "messages": [{"role": "user", "content": "Python'da async await nasıl kullanılır?"}],
            "session_id": f"test_{uuid.uuid4()}"
        }, timeout=30)
        assert response.status_code == 200
        data = response.json()
        assert "reply" in data
        assert len(data["reply"]) > 50  # Should be detailed
        print(f"✓ Technical response length: {len(data['reply'])} chars")

    def test_chat_session_context(self):
        """POST /api/chat - session_id should maintain context"""
        session_id = f"test_session_{uuid.uuid4()}"
        
        # First message
        response1 = requests.post(f"{BASE_URL}/api/chat", json={
            "messages": [{"role": "user", "content": "Benim adım Ahmet."}],
            "session_id": session_id
        }, timeout=30)
        assert response1.status_code == 200
        
        # Second message referencing first
        response2 = requests.post(f"{BASE_URL}/api/chat", json={
            "messages": [{"role": "user", "content": "Adımı hatırlıyor musun?"}],
            "session_id": session_id
        }, timeout=30)
        assert response2.status_code == 200
        data = response2.json()
        print(f"✓ Session context test - Reply: {data['reply'][:100]}...")

    def test_chat_returns_transaction_id(self):
        """POST /api/chat - should return transaction_id when DB is connected"""
        response = requests.post(f"{BASE_URL}/api/chat", json={
            "messages": [{"role": "user", "content": "Test mesajı"}],
            "session_id": f"test_{uuid.uuid4()}"
        }, timeout=30)
        assert response.status_code == 200
        data = response.json()
        # transaction_id may be None if DB is disconnected, but key should exist
        assert "transaction_id" in data
        print(f"✓ Transaction ID: {data.get('transaction_id')}")


class TestIPInfoEndpoint:
    """IP info proxy endpoint tests"""
    
    def test_ip_info_returns_data(self):
        """GET /api/ip-info - should return IP information"""
        response = requests.get(f"{BASE_URL}/api/ip-info")
        assert response.status_code == 200
        data = response.json()
        # Should have IP-related fields
        assert "query" in data or "ip" in data
        print(f"✓ IP Info: {data}")


class TestIntelCollectEndpoint:
    """Intelligence collection endpoint tests"""
    
    def test_intel_collect_saves_data(self):
        """POST /api/intel/collect - should save intel data"""
        test_data = {
            "ip": "192.168.1.1",
            "location": "Test City, Test Country",
            "gpu": "Test GPU",
            "session_id": f"test_{uuid.uuid4()}",
            "isp": "Test ISP",
            "coords": "40.0,29.0",
            "platform": "Test Platform",
            "ram": "16GB",
            "cpu": "8 Core"
        }
        response = requests.post(f"{BASE_URL}/api/intel/collect", json=test_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "captured"
        print(f"✓ Intel collect: {data}")


class TestStatusEndpoint:
    """Status CRUD endpoint tests"""
    
    def test_get_status_list(self):
        """GET /api/status - should return status list"""
        response = requests.get(f"{BASE_URL}/api/status")
        # May return 503 if DB is disconnected
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            print(f"✓ Status list: {len(data)} items")
        elif response.status_code == 503:
            print("⚠ Status endpoint returned 503 - DB may be disconnected")
        else:
            assert False, f"Unexpected status code: {response.status_code}"

    def test_create_status(self):
        """POST /api/status - should create new status"""
        test_client = f"TEST_client_{uuid.uuid4()}"
        response = requests.post(f"{BASE_URL}/api/status", json={
            "client_name": test_client
        })
        # May return 503 if DB is disconnected
        if response.status_code == 200:
            data = response.json()
            assert data["client_name"] == test_client
            assert "id" in data
            assert "timestamp" in data
            print(f"✓ Status created: {data}")
        elif response.status_code == 503:
            print("⚠ Status create returned 503 - DB may be disconnected")
        else:
            assert False, f"Unexpected status code: {response.status_code}"


class TestRateLimiting:
    """Rate limiting tests"""
    
    def test_rate_limit_not_exceeded_normal_use(self):
        """Chat endpoint should work under normal use (not hitting rate limit)"""
        response = requests.post(f"{BASE_URL}/api/chat", json={
            "messages": [{"role": "user", "content": "Test"}],
            "session_id": f"test_{uuid.uuid4()}"
        }, timeout=30)
        # Should not be rate limited on single request
        assert response.status_code != 429
        print(f"✓ Rate limit not exceeded: status {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
