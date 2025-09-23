#!/usr/bin/env python3
"""
Test script to debug user role checking
"""

import requests
import json

BASE_URL = "http://localhost:5001"

def test_user_roles():
    """Test user role checking for specific emails"""
    
    # Test emails
    test_emails = [
        "mstfssk@gmail.com",      # Should be admin
        "bogazicimodule@gmail.com"  # Should be editor
    ]
    
    print("🔍 Testing user role checking...")
    print("=" * 50)
    
    for email in test_emails:
        print(f"\n📧 Testing email: {email}")
        
        # First, try to find user by email in Firestore
        print("1. Checking if user exists in Firestore...")
        
        # You can manually check this in Firebase Console
        print(f"   - Go to Firebase Console > Firestore > users collection")
        print(f"   - Look for document with email: {email}")
        print(f"   - Check if role field exists and what value it has")
        
        print("\n2. To test with actual login:")
        print(f"   - Go to {BASE_URL}/login")
        print(f"   - Login with email: {email}")
        print(f"   - Check browser console for role logs")
        print(f"   - Check navbar for admin/editor panel links")
        
        print("\n3. Debug endpoint (after login):")
        print(f"   - GET {BASE_URL}/api/debug/user-info")
        print(f"   - This will show all user info and role data")
        
        print("\n" + "-" * 30)

def test_firebase_connection():
    """Test Firebase connection"""
    print("\n🔥 Testing Firebase connection...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/firebase-status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Firebase status: {data}")
        else:
            print(f"❌ Firebase status check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing Firebase connection: {e}")

def test_auth_status():
    """Test authentication status (if logged in)"""
    print("\n🔐 Testing authentication status...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/auth/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Auth status: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ Auth status check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing auth status: {e}")

if __name__ == "__main__":
    print("🧪 SmartQRMenu Role Testing Script")
    print("=" * 50)
    
    test_firebase_connection()
    test_user_roles()
    test_auth_status()
    
    print("\n📋 Manual Testing Steps:")
    print("1. Start the application: python app.py")
    print("2. Open browser and go to http://localhost:5001")
    print("3. Login with mstfssk@gmail.com (should see admin panel)")
    print("4. Login with bogazicimodule@gmail.com (should see editor panel)")
    print("5. Check browser console for role checking logs")
    print("6. Check navbar dropdown for admin/editor panel links")
