#!/usr/bin/env python3
"""
SIMPLE FIREBASE TEST APP
This will tell you EXACTLY what's wrong with Firebase
"""

import os
import json
import traceback
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Global variables
db = None
firebase_app = None
firebase_status = "Not tested"
firebase_error = None

def test_firebase_step_by_step():
    """Test Firebase initialization step by step"""
    global db, firebase_app, firebase_status, firebase_error
    
    steps = []
    
    # Step 1: Check environment variable
    try:
        firebase_creds = os.getenv('FIREBASE_CREDENTIALS')
        if not firebase_creds:
            steps.append("❌ FIREBASE_CREDENTIALS environment variable not found")
            firebase_status = "ENV_VAR_MISSING"
            firebase_error = "FIREBASE_CREDENTIALS environment variable not set"
            return steps
        else:
            steps.append("✅ FIREBASE_CREDENTIALS environment variable found")
    except Exception as e:
        steps.append(f"❌ Error checking environment: {e}")
        firebase_status = "ENV_ERROR"
        firebase_error = str(e)
        return steps
    
    # Step 2: Parse JSON
    try:
        firebase_json = json.loads(firebase_creds)
        steps.append("✅ Firebase JSON parsed successfully")
        
        # Check required fields
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in firebase_json]
        
        if missing_fields:
            steps.append(f"❌ Missing required fields: {missing_fields}")
            firebase_status = "INVALID_JSON"
            firebase_error = f"Missing fields: {missing_fields}"
            return steps
        else:
            steps.append("✅ All required JSON fields present")
            steps.append(f"   Project ID: {firebase_json.get('project_id')}")
            steps.append(f"   Client Email: {firebase_json.get('client_email')}")
    except json.JSONDecodeError as e:
        steps.append(f"❌ Invalid JSON format: {e}")
        firebase_status = "JSON_ERROR"
        firebase_error = f"JSON parsing error: {e}"
        return steps
    except Exception as e:
        steps.append(f"❌ Error parsing JSON: {e}")
        firebase_status = "JSON_ERROR"
        firebase_error = str(e)
        return steps
    
    # Step 3: Import Firebase modules
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        steps.append("✅ Firebase modules imported successfully")
    except ImportError as e:
        steps.append(f"❌ Firebase modules import failed: {e}")
        firebase_status = "IMPORT_ERROR"
        firebase_error = f"Import error: {e}"
        return steps
    except Exception as e:
        steps.append(f"❌ Error importing Firebase: {e}")
        firebase_status = "IMPORT_ERROR"
        firebase_error = str(e)
        return steps
    
    # Step 4: Initialize Firebase
    try:
        # Check if already initialized
        if firebase_admin._apps:
            steps.append("✅ Firebase already initialized")
            firebase_app = firebase_admin.get_app()
        else:
            cred = credentials.Certificate(firebase_json)
            firebase_app = firebase_admin.initialize_app(cred)
            steps.append("✅ Firebase app initialized successfully")
    except Exception as e:
        steps.append(f"❌ Firebase initialization failed: {e}")
        steps.append(f"   Full error: {traceback.format_exc()}")
        firebase_status = "INIT_ERROR"
        firebase_error = str(e)
        return steps
    
    # Step 5: Get Firestore client
    try:
        db = firestore.client()
        steps.append("✅ Firestore client created successfully")
    except Exception as e:
        steps.append(f"❌ Firestore client creation failed: {e}")
        firebase_status = "FIRESTORE_ERROR"
        firebase_error = str(e)
        return steps
    
    # Step 6: Test write operation
    try:
        test_ref = db.collection('test').document('connection_test')
        test_ref.set({
            'test': True,
            'timestamp': datetime.now(),
            'message': 'Firebase test successful'
        })
        steps.append("✅ Test document written successfully")
    except Exception as e:
        steps.append(f"❌ Test write failed: {e}")
        firebase_status = "WRITE_ERROR"
        firebase_error = str(e)
        return steps
    
    # Step 7: Test read operation
    try:
        doc = test_ref.get()
        if doc.exists:
            steps.append("✅ Test document read successfully")
            steps.append(f"   Document data: {doc.to_dict()}")
        else:
            steps.append("❌ Test document not found after write")
            firebase_status = "READ_ERROR"
            firebase_error = "Document not found after write"
            return steps
    except Exception as e:
        steps.append(f"❌ Test read failed: {e}")
        firebase_status = "READ_ERROR"
        firebase_error = str(e)
        return steps
    
    # Step 8: Test collection operations
    try:
        # Add a few test documents
        test_collection = db.collection('test_users')
        test_collection.document('user1').set({'name': 'Test User 1', 'created': datetime.now()})
        test_collection.document('user2').set({'name': 'Test User 2', 'created': datetime.now()})
        
        # Read all documents
        docs = test_collection.stream()
        doc_count = len(list(docs))
        steps.append(f"✅ Collection operations successful ({doc_count} documents)")
    except Exception as e:
        steps.append(f"❌ Collection operations failed: {e}")
        firebase_status = "COLLECTION_ERROR"
        firebase_error = str(e)
        return steps
    
    # All tests passed!
    firebase_status = "SUCCESS"
    firebase_error = None
    steps.append("🎉 ALL FIREBASE TESTS PASSED!")
    
    return steps

@app.route('/')
def home():
    """Main test page"""
    steps = test_firebase_step_by_step()
    
    steps_html = "<br>".join(steps)
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Firebase Test App</title>
        <style>
            body {{ 
                font-family: 'Courier New', monospace; 
                margin: 20px; 
                background-color: #f5f5f5; 
            }}
            .container {{ 
                max-width: 800px; 
                margin: 0 auto; 
                background: white; 
                padding: 20px; 
                border-radius: 8px; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
            }}
            .status {{ 
                padding: 15px; 
                margin: 10px 0; 
                border-radius: 5px; 
                font-weight: bold; 
            }}
            .success {{ 
                background-color: #d4edda; 
                color: #155724; 
                border: 1px solid #c3e6cb; 
            }}
            .error {{ 
                background-color: #f8d7da; 
                color: #721c24; 
                border: 1px solid #f5c6cb; 
            }}
            .warning {{ 
                background-color: #fff3cd; 
                color: #856404; 
                border: 1px solid #ffeaa7; 
            }}
            .steps {{ 
                background-color: #f8f9fa; 
                padding: 15px; 
                border-radius: 5px; 
                font-family: 'Courier New', monospace; 
                white-space: pre-wrap; 
            }}
            .refresh {{ 
                background-color: #007bff; 
                color: white; 
                padding: 10px 20px; 
                border: none; 
                border-radius: 5px; 
                cursor: pointer; 
                font-size: 16px; 
                margin: 10px 0; 
            }}
            .refresh:hover {{ 
                background-color: #0056b3; 
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔥 Firebase Test App</h1>
            
            <div class="status {'success' if firebase_status == 'SUCCESS' else 'error'}">
                <strong>Firebase Status:</strong> {firebase_status}
                {f'<br><strong>Error:</strong> {firebase_error}' if firebase_error else ''}
            </div>
            
            <button class="refresh" onclick="location.reload()">🔄 Refresh Test</button>
            
            <h2>📋 Test Steps:</h2>
            <div class="steps">{steps_html}</div>
            
            <h2>🔧 Troubleshooting:</h2>
            <ul>
                <li><strong>ENV_VAR_MISSING:</strong> Add FIREBASE_CREDENTIALS to Render environment</li>
                <li><strong>JSON_ERROR:</strong> Check your Firebase JSON format - must be single line</li>
                <li><strong>IMPORT_ERROR:</strong> Install firebase-admin: pip install firebase-admin</li>
                <li><strong>INIT_ERROR:</strong> Check Firebase project permissions</li>
                <li><strong>WRITE_ERROR:</strong> Check Firestore security rules</li>
            </ul>
            
            <h2>📝 Environment Variables:</h2>
            <ul>
                <li><strong>FIREBASE_CREDENTIALS:</strong> {'✅ SET' if os.getenv('FIREBASE_CREDENTIALS') else '❌ MISSING'}</li>
            </ul>
            
            <p><em>Last tested: {datetime.now()}</em></p>
        </div>
    </body>
    </html>
    """

@app.route('/test-add-user')
def test_add_user():
    """Test adding a user to Firebase"""
    if firebase_status != "SUCCESS" or not db:
        return {"error": "Firebase not initialized", "status": firebase_status}
    
    try:
        # Add a test user
        user_ref = db.collection('group_members').document('test_user_123')
        user_ref.set({
            'name': 'Test User',
            'phone': '+1234567890',
            'joined_at': datetime.now(),
            'test': True
        })
        
        return {"message": "User added successfully", "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}

@app.route('/test-get-users')
def test_get_users():
    """Test getting users from Firebase"""
    if firebase_status != "SUCCESS" or not db:
        return {"error": "Firebase not initialized", "status": firebase_status}
    
    try:
        # Get all users
        users_ref = db.collection('group_members')
        docs = users_ref.stream()
        
        users = []
        for doc in docs:
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            users.append(user_data)
        
        return {"users": users, "count": len(users), "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}

@app.route('/firebase-info')
def firebase_info():
    """Get Firebase configuration info"""
    firebase_creds = os.getenv('FIREBASE_CREDENTIALS')
    
    if not firebase_creds:
        return {"error": "No Firebase credentials found"}
    
    try:
        firebase_json = json.loads(firebase_creds)
        return {
            "project_id": firebase_json.get('project_id'),
            "client_email": firebase_json.get('client_email'),
            "type": firebase_json.get('type'),
            "has_private_key": 'private_key' in firebase_json,
            "status": firebase_status
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
