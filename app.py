# app.py - WhatsApp Inventory Bot with Extensive Debugging
import os
import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime
import re
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Environment variables
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN')

# Debug: Print environment variables (masked)
print("=== ENVIRONMENT VARIABLES DEBUG ===")
print(f"WHATSAPP_TOKEN: {'SET' if WHATSAPP_TOKEN else 'NOT SET'}")
print(f"WHATSAPP_PHONE_NUMBER_ID: {'SET' if WHATSAPP_PHONE_NUMBER_ID else 'NOT SET'}")
print(f"VERIFY_TOKEN: {'SET' if VERIFY_TOKEN else 'NOT SET'}")
if WHATSAPP_TOKEN:
    print(f"Token preview: {WHATSAPP_TOKEN[:10]}...{WHATSAPP_TOKEN[-10:]}")
if WHATSAPP_PHONE_NUMBER_ID:
    print(f"Phone Number ID: {WHATSAPP_PHONE_NUMBER_ID}")
print("=====================================")

# Simple inventory storage
inventory = {}

def send_whatsapp_message(to_number, message):
    """Send WhatsApp message with detailed debugging"""
    
    print(f"\n=== ATTEMPTING TO SEND MESSAGE ===")
    print(f"To: {to_number}")
    print(f"Message: {message}")
    print(f"Using Phone Number ID: {WHATSAPP_PHONE_NUMBER_ID}")
    print(f"Using Token: {WHATSAPP_TOKEN[:10]}...{WHATSAPP_TOKEN[-10:] if WHATSAPP_TOKEN else 'None'}")
    
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        'Authorization': f'Bearer {WHATSAPP_TOKEN}',
        'Content-Type': 'application/json',
    }
    
    data = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {
            "body": message
        }
    }
    
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"Response Status: {response.status_code}")
        print(f"Response Text: {response.text}")
        
        if response.status_code == 200:
            print("✅ MESSAGE SENT SUCCESSFULLY!")
            return True
        else:
            print(f"❌ MESSAGE FAILED!")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION OCCURRED: {str(e)}")
        return False

def process_inventory_command(message_text, sender_number):
    """Process inventory commands with debugging"""
    
    print(f"\n=== PROCESSING COMMAND ===")
    print(f"From: {sender_number}")
    print(f"Message: {message_text}")
    
    message_text = message_text.lower().strip()
    
    if message_text == "help":
        response = """🤖 WhatsApp Inventory Bot Commands:

📦 *Initialize inventory:*
apple=5, banana=12, table=10

➕ *Add items:*
add apple=3

➖ *Sell items:*
sell banana=5

📋 *Show inventory:*
inventory

❓ *Get help:*
help

Example: apple=10, banana=5"""
        return response
    
    elif message_text == "inventory":
        if not inventory:
            return "📦 Inventory is empty. Initialize with: apple=5, banana=10"
        
        response = "📦 *Current Inventory:*\n"
        for item, quantity in inventory.items():
            response += f"• {item}: {quantity}\n"
        return response
    
    elif message_text.startswith("add "):
        # Parse add command
        try:
            item_data = message_text[4:].strip()  # Remove "add "
            if "=" in item_data:
                item, quantity = item_data.split("=", 1)
                item = item.strip()
                quantity = int(quantity.strip())
                
                if item in inventory:
                    inventory[item] += quantity
                else:
                    inventory[item] = quantity
                
                return f"✅ Added {quantity} {item}(s). New quantity: {inventory[item]}"
            else:
                return "❌ Format: add apple=5"
        except ValueError:
            return "❌ Invalid quantity. Use numbers only."
    
    elif message_text.startswith("sell "):
        # Parse sell command
        try:
            item_data = message_text[5:].strip()  # Remove "sell "
            if "=" in item_data:
                item, quantity = item_data.split("=", 1)
                item = item.strip()
                quantity = int(quantity.strip())
                
                if item not in inventory:
                    return f"❌ {item} not found in inventory"
                
                if inventory[item] < quantity:
                    return f"❌ Not enough {item}. Available: {inventory[item]}"
                
                inventory[item] -= quantity
                if inventory[item] == 0:
                    del inventory[item]
                
                return f"✅ Sold {quantity} {item}(s). Remaining: {inventory.get(item, 0)}"
            else:
                return "❌ Format: sell apple=3"
        except ValueError:
            return "❌ Invalid quantity. Use numbers only."
    
    elif "=" in message_text:
        # Initialize inventory
        try:
            items = message_text.split(",")
            for item in items:
                if "=" in item:
                    name, quantity = item.split("=", 1)
                    name = name.strip()
                    quantity = int(quantity.strip())
                    inventory[name] = quantity
            
            response = "✅ Inventory initialized:\n"
            for item, quantity in inventory.items():
                response += f"• {item}: {quantity}\n"
            return response
        except ValueError:
            return "❌ Invalid format. Use: apple=5, banana=10"
    
    else:
        return "❌ Unknown command. Type 'help' for commands."

@app.route('/')
def home():
    return "🤖 WhatsApp Inventory Bot is Running!"

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "whatsapp_token": "SET" if WHATSAPP_TOKEN else "NOT SET",
            "phone_number_id": "SET" if WHATSAPP_PHONE_NUMBER_ID else "NOT SET",
            "verify_token": "SET" if VERIFY_TOKEN else "NOT SET"
        }
    })

@app.route('/debug')
def debug():
    """Debug endpoint to check configuration"""
    return jsonify({
        "whatsapp_token": WHATSAPP_TOKEN[:10] + "..." + WHATSAPP_TOKEN[-10:] if WHATSAPP_TOKEN else "NOT SET",
        "phone_number_id": WHATSAPP_PHONE_NUMBER_ID,
        "verify_token": VERIFY_TOKEN,
        "inventory": inventory
    })

@app.route('/test-send')
def test_send():
    """Test endpoint to send a message manually"""
    test_number = request.args.get('number')
    if not test_number:
        return "Usage: /test-send?number=1234567890"
    
    success = send_whatsapp_message(test_number, "🤖 Test message from WhatsApp Bot!")
    return f"Message sent: {success}"

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """WhatsApp webhook endpoint with extensive debugging"""
    
    print(f"\n=== WEBHOOK CALLED ===")
    print(f"Method: {request.method}")
    print(f"Headers: {dict(request.headers)}")
    print(f"Args: {dict(request.args)}")
    
    if request.method == 'GET':
        # Webhook verification
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        print(f"Verification attempt:")
        print(f"Mode: {mode}")
        print(f"Token received: {token}")
        print(f"Token expected: {VERIFY_TOKEN}")
        print(f"Challenge: {challenge}")
        
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print("✅ Webhook verified successfully!")
            return challenge
        else:
            print("❌ Webhook verification failed!")
            return "Verification failed", 403
    
    elif request.method == 'POST':
        # Handle incoming messages
        try:
            data = request.get_json()
            print(f"Received data: {json.dumps(data, indent=2)}")
            
            if not data:
                print("❌ No data received")
                return "No data", 400
            
            # Check if it's a message
            if 'entry' in data:
                for entry in data['entry']:
                    if 'changes' in entry:
                        for change in entry['changes']:
                            if 'value' in change and 'messages' in change['value']:
                                for message in change['value']['messages']:
                                    sender_number = message['from']
                                    message_text = message.get('text', {}).get('body', '')
                                    
                                    print(f"Processing message from {sender_number}: {message_text}")
                                    
                                    # Process the command
                                    response = process_inventory_command(message_text, sender_number)
                                    
                                    # Send response
                                    print(f"Sending response: {response}")
                                    success = send_whatsapp_message(sender_number, response)
                                    
                                    if success:
                                        print("✅ Response sent successfully")
                                    else:
                                        print("❌ Failed to send response")
            
            return "OK", 200
            
        except Exception as e:
            print(f"❌ Error processing webhook: {str(e)}")
            return f"Error: {str(e)}", 500
    
    return "Method not allowed", 405

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
