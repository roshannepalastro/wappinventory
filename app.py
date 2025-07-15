#!/usr/bin/env python3
"""
SUPER SIMPLE BOT - NO FIREBASE
This WILL work. Period.
"""

import os
import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Just use memory - no Firebase headaches
MEMBERS = {}

# Get WhatsApp credentials
WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')

def send_whatsapp_message(to_number, message_text):
    """Send WhatsApp message"""
    url = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": message_text}
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return True
    except:
        return False

def process_command(message_text, sender_number):
    """Process commands - SUPER SIMPLE"""
    message_text = message_text.lower().strip()
    sender_name = f"User{sender_number[-4:]}"
    
    if message_text == "join":
        if sender_number in MEMBERS:
            return f"✅ {sender_name}, you're already in the group!"
        
        MEMBERS[sender_number] = {
            'name': sender_name,
            'joined_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        return f"✅ Welcome {sender_name}! You joined the group."
    
    elif message_text == "leave":
        if sender_number not in MEMBERS:
            return f"❌ {sender_name}, you're not in the group."
        
        del MEMBERS[sender_number]
        return f"✅ {sender_name}, you left the group."
    
    elif message_text == "members":
        if not MEMBERS:
            return "📋 No members in the group."
        
        member_list = "👥 Group Members:\n"
        for i, (phone, data) in enumerate(MEMBERS.items(), 1):
            member_list += f"{i}. {data['name']} (joined: {data['joined_at']})\n"
        
        return member_list
    
    elif message_text == "help":
        return """🤖 Available Commands:
        
join - Join the group
leave - Leave the group  
members - View all members
help - Show this help"""
    
    else:
        return f"❓ Unknown command. Send 'help' for available commands."

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Webhook verification
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return challenge
        else:
            return 'Forbidden', 403
    
    elif request.method == 'POST':
        # Handle incoming messages
        data = request.get_json()
        
        try:
            entry = data.get('entry', [{}])[0]
            changes = entry.get('changes', [{}])[0]
            value = changes.get('value', {})
            messages = value.get('messages', [])
            
            if messages:
                message = messages[0]
                sender_number = message.get('from')
                message_text = message.get('text', {}).get('body', '')
                
                # Process command
                response = process_command(message_text, sender_number)
                
                # Send response
                send_whatsapp_message(sender_number, response)
                    
        except Exception as e:
            print(f"Error: {e}")
        
        return jsonify({"status": "ok"})

@app.route('/')
def home():
    """Status page"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simple WhatsApp Bot</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
            .success {{ background-color: #d4edda; color: #155724; }}
            .error {{ background-color: #f8d7da; color: #721c24; }}
        </style>
    </head>
    <body>
        <h1>🤖 Simple WhatsApp Bot</h1>
        
        <div class="status {'success' if WHATSAPP_ACCESS_TOKEN else 'error'}">
            <strong>WhatsApp Token:</strong> {'✅ Ready' if WHATSAPP_ACCESS_TOKEN else '❌ Missing'}
        </div>
        
        <div class="status {'success' if WHATSAPP_PHONE_NUMBER_ID else 'error'}">
            <strong>Phone Number ID:</strong> {'✅ Ready' if WHATSAPP_PHONE_NUMBER_ID else '❌ Missing'}
        </div>
        
        <div class="status {'success' if VERIFY_TOKEN else 'error'}">
            <strong>Verify Token:</strong> {'✅ Ready' if VERIFY_TOKEN else '❌ Missing'}
        </div>
        
        <div class="status success">
            <strong>Current Members:</strong> {len(MEMBERS)} people in group
        </div>
        
        <h2>Commands:</h2>
        <ul>
            <li><strong>join</strong> - Join the group</li>
            <li><strong>leave</strong> - Leave the group</li>
            <li><strong>members</strong> - View all members</li>
            <li><strong>help</strong> - Show help</li>
        </ul>
        
        <h2>Current Members:</h2>
        {'<ul>' + ''.join([f'<li>{data["name"]} (joined: {data["joined_at"]})</li>' for data in MEMBERS.values()]) + '</ul>' if MEMBERS else '<p>No members yet</p>'}
        
        <p><em>Updated: {datetime.now()}</em></p>
    </body>
    </html>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
