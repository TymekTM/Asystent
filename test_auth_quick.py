#!/usr/bin/env python3
"""
Test autoryzacji z nowymi danymi i protected endpoints
"""

import requests
import json

def test_auth():
    url = "http://localhost:8001/api/v1/auth/login"
    
    # Test admin@gaja.app
    login_data = {
        "email": "admin@gaja.app",
        "password": "admin123"
    }
    
    print("🔐 Testowanie logowania admin@gaja.app...")
    response = requests.post(url, json=login_data)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Logowanie udane!")
        token = data.get('token')
        print(f"Token: {token}")
        
        if token:
            # Test protected endpoint /me
            print("\n🔒 Testowanie protected endpoint /me...")
            headers = {"Authorization": f"Bearer {token}"}
            me_response = requests.get("http://localhost:8001/api/v1/me", headers=headers)
            
            print(f"/me Status: {me_response.status_code}")
            print(f"/me Response: {me_response.text}")
            
            # Test AI query endpoint
            print("\n🤖 Testowanie AI query endpoint...")
            ai_query = {
                "query": "Hello, this is a test query"
            }
            ai_response = requests.post("http://localhost:8001/api/v1/ai/query", headers=headers, json=ai_query)
            
            print(f"/ai/query Status: {ai_response.status_code}")
            print(f"/ai/query Response: {ai_response.text[:500]}...")  # Truncate long response
        
        return True
    else:
        print(f"❌ Logowanie nieudane")
        return False

if __name__ == "__main__":
    test_auth()
