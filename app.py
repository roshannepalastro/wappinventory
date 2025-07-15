# group_admin_bot.py - Alternative Group Management Solution
import os
import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Group admin configuration
GROUP_ADMINS = {
    "9779816034951": "Admin User 1",  # Your number
    # Add more admin numbers here
}

# Store group member numbers
GROUP_MEMBERS = set()

# Enhanced inventory with group features
inventory = {}
inventory_updates = []  # Store update history

def is_group_admin(phone_number):
    """Check if user is group admin"""
    return phone_number in GROUP_ADMINS

def send_whatsapp_message(to_number, message):
    """Send WhatsApp message using Graph API"""
    try:
        # WhatsApp Business API credentials
        access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        
        print(f"🔍 Checking WhatsApp API credentials:")
        print(f"  Access token set: {access_token is not None}")
        print(f"  Phone number ID set: {phone_number_id is not None}")
        
        if not access_token:
            print("❌ WHATSAPP_ACCESS_TOKEN environment variable not set!")
            return False
            
        if not phone_number_id:
            print("❌ WHATSAPP_PHONE_NUMBER_ID environment variable not set!")
            return False
        
        print(f"  Access token length: {len(access_token)}")
        print(f"  Phone number ID: {phone_number_id}")
        
        url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
        print(f"  API URL: {url}")
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {
                "body": message
            }
        }
        
        print(f"  Sending to: {to_number}")
        print(f"  Message length: {len(message)}")
        
        response = requests.post(url, headers=headers, json=payload)
        
        print(f"  Response status: {response.status_code}")
        print(f"  Response body: {response.text}")
        
        if response.status_code == 200:
            print(f"✅ Message sent successfully to {to_number}")
            return True
        else:
            print(f"❌ Failed to send message to {to_number}: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending message: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def broadcast_to_group(message, exclude_number=None):
    """Send message to all group members"""
    sent_count = 0
    for member in GROUP_MEMBERS:
        if member != exclude_number:
            if send_whatsapp_message(member, message):
                sent_count += 1
    return sent_count

def process_group_inventory_command(message_text, sender_number):
    """Process inventory commands with group features"""
    
    message_text = message_text.lower().strip()
    sender_name = GROUP_ADMINS.get(sender_number, f"User {sender_number[-4:]}")
    
    # Join group command
    if message_text == "join":
        if sender_number not in GROUP_MEMBERS:
            GROUP_MEMBERS.add(sender_number)
            response = f"✅ {sender_name} joined the inventory group!\n"
            response += f"👥 Total members: {len(GROUP_MEMBERS)}\n"
            response += "Type 'help' for commands."
            
            # Notify other members
            broadcast_message = f"👋 {sender_name} joined the inventory group!"
            broadcast_to_group(broadcast_message, exclude_number=sender_number)
            
            return response
        else:
            return "✅ You're already in the group!"
    
    # Leave group command
    elif message_text == "leave":
        if sender_number in GROUP_MEMBERS:
            GROUP_MEMBERS.remove(sender_number)
            broadcast_message = f"👋 {sender_name} left the inventory group"
            broadcast_to_group(broadcast_message, exclude_number=sender_number)
            return "✅ You left the inventory group"
        else:
            return "❌ You're not in the group"
    
    # Check if user is in group
    if sender_number not in GROUP_MEMBERS:
        return "❌ You must join the group first. Send 'join' to participate."
    
    # Group help command
    if message_text == "help":
        response = """🤖 *WhatsApp Group Inventory Bot*

👥 *Group Commands:*
• join - Join the inventory group
• leave - Leave the group
• members - Show group members
• broadcast <message> - Send to all members (admin only)

📦 *Inventory Commands:*
• inventory - Show current stock
• add apple=5 - Add items to stock
• sell banana=3 - Remove items from stock
• history - Show recent updates
• apple=10, banana=5 - Initialize inventory

🔧 *Admin Commands:*
• reset - Clear all inventory (admin only)
• kick <number> - Remove member (admin only)

💡 *Examples:*
• apple=10, banana=5, orange=8
• add apple=5
• sell banana=3"""
        return response
    
    # Show group members
    elif message_text == "members":
        if not GROUP_MEMBERS:
            return "👥 No members in the group"
        
        response = f"👥 *Group Members ({len(GROUP_MEMBERS)}):*\n"
        for i, member in enumerate(GROUP_MEMBERS, 1):
            member_name = GROUP_ADMINS.get(member, f"User {member[-4:]}")
            admin_badge = " 👑" if is_group_admin(member) else ""
            response += f"{i}. {member_name}{admin_badge}\n"
        return response
    
    # Broadcast message (admin only)
    elif message_text.startswith("broadcast "):
        if not is_group_admin(sender_number):
            return "❌ Only admins can broadcast messages"
        
        broadcast_msg = message_text[10:].strip()
        if not broadcast_msg:
            return "❌ Usage: broadcast <your message>"
        
        full_message = f"📢 *Broadcast from {sender_name}:*\n{broadcast_msg}"
        sent_count = broadcast_to_group(full_message, exclude_number=sender_number)
        
        return f"✅ Message sent to {sent_count} members"
    
    # Reset inventory (admin only)
    elif message_text == "reset":
        if not is_group_admin(sender_number):
            return "❌ Only admins can reset inventory"
        
        inventory.clear()
        inventory_updates.clear()
        
        # Notify group
        broadcast_message = f"🔄 {sender_name} reset the inventory"
        broadcast_to_group(broadcast_message, exclude_number=sender_number)
        
        return "✅ Inventory reset successfully"
    
    # Show inventory
    elif message_text == "inventory":
        if not inventory:
            return "📦 Inventory is empty"
        
        response = "📦 *Current Inventory:*\n"
        total_items = 0
        for item, quantity in inventory.items():
            response += f"• {item}: {quantity}\n"
            total_items += quantity
        
        response += f"\n📊 Total items: {total_items}"
        return response
    
    # Show update history
    elif message_text == "history":
        if not inventory_updates:
            return "📋 No inventory updates yet"
        
        response = "📋 *Recent Updates:*\n"
        # Show last 5 updates
        for update in inventory_updates[-5:]:
            response += f"• {update}\n"
        
        return response
    
    # Add items
    elif message_text.startswith("add "):
        try:
            item_data = message_text[4:].strip()
            if "=" in item_data:
                item, quantity = item_data.split("=", 1)
                item = item.strip()
                quantity = int(quantity.strip())
                
                if item in inventory:
                    inventory[item] += quantity
                else:
                    inventory[item] = quantity
                
                # Log update
                update_log = f"{sender_name} added {quantity} {item}(s) at {datetime.now().strftime('%H:%M')}"
                inventory_updates.append(update_log)
                
                response = f"✅ Added {quantity} {item}(s)\n"
                response += f"📦 New quantity: {inventory[item]}"
                
                # Notify group
                broadcast_message = f"➕ {sender_name} added {quantity} {item}(s) to inventory"
                broadcast_to_group(broadcast_message, exclude_number=sender_number)
                
                return response
            else:
                return "❌ Format: add apple=5"
        except ValueError:
            return "❌ Invalid quantity. Use numbers only."
    
    # Sell items
    elif message_text.startswith("sell "):
        try:
            item_data = message_text[5:].strip()
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
                
                # Log update
                update_log = f"{sender_name} sold {quantity} {item}(s) at {datetime.now().strftime('%H:%M')}"
                inventory_updates.append(update_log)
                
                response = f"✅ Sold {quantity} {item}(s)\n"
                response += f"📦 Remaining: {inventory.get(item, 0)}"
                
                # Notify group
                broadcast_message = f"➖ {sender_name} sold {quantity} {item}(s) from inventory"
                broadcast_to_group(broadcast_message, exclude_number=sender_number)
                
                return response
            else:
                return "❌ Format: sell apple=3"
        except ValueError:
            return "❌ Invalid quantity. Use numbers only."
    
    # Initialize inventory
    elif "=" in message_text:
        try:
            items = message_text.split(",")
            updated_items = []
            
            for item in items:
                if "=" in item:
                    name, quantity = item.split("=", 1)
                    name = name.strip()
                    quantity = int(quantity.strip())
                    inventory[name] = quantity
                    updated_items.append(f"{name}: {quantity}")
            
            if updated_items:
                # Log update
                update_log = f"{sender_name} updated inventory at {datetime.now().strftime('%H:%M')}"
                inventory_updates.append(update_log)
                
                response = "✅ Inventory updated:\n"
                for item in updated_items:
                    response += f"• {item}\n"
                
                # Notify group
                broadcast_message = f"🔄 {sender_name} updated the inventory"
                broadcast_to_group(broadcast_message, exclude_number=sender_number)
                
                return response
            else:
                return "❌ Invalid format. Use: apple=5, banana=10"
        except ValueError:
            return "❌ Invalid format. Use: apple=5, banana=10"
    
    else:
        return "❌ Unknown command. Type 'help' for available commands."

# Add root route to handle home page
@app.route('/')
def home():
    """Landing page for the inventory bot"""
    # Use f-string to avoid conflicts with CSS braces
    group_count = len(GROUP_MEMBERS)
    inventory_count = len(inventory)
    updates_count = len(inventory_updates)
    webhook_url = f"{request.host_url}webhook"
    
    return f"""
    <html>
    <head>
        <title>WhatsApp Inventory Bot</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
            h1 {{ color: #25d366; }}
            .status {{ background: #e8f5e8; padding: 10px; border-radius: 5px; margin: 20px 0; }}
            .command {{ background: #f0f0f0; padding: 5px; margin: 5px 0; font-family: monospace; }}
        </style>
    </head>
    <body>
        <h1>🤖 WhatsApp Inventory Bot</h1>
        
        <div class="status">
            <strong>✅ Bot Status:</strong> Online and Ready
        </div>
        
        <h2>📱 How to Use:</h2>
        <p>Send these commands to your WhatsApp bot:</p>
        
        <h3>👥 Group Commands:</h3>
        <div class="command">join</div>
        <div class="command">leave</div>
        <div class="command">members</div>
        <div class="command">broadcast &lt;message&gt;</div>
        
        <h3>📦 Inventory Commands:</h3>
        <div class="command">inventory</div>
        <div class="command">add apple=5</div>
        <div class="command">sell banana=3</div>
        <div class="command">history</div>
        <div class="command">apple=10, banana=5</div>
        
        <h3>🔧 Admin Commands:</h3>
        <div class="command">reset</div>
        <div class="command">help</div>
        
        <h2>📊 Current Status:</h2>
        <p><strong>Group Members:</strong> {group_count}</p>
        <p><strong>Inventory Items:</strong> {inventory_count}</p>
        <p><strong>Recent Updates:</strong> {updates_count}</p>
        
        <div class="status">
            <strong>🔗 Webhook URL:</strong> {webhook_url}
        </div>
    </body>
    </html>
    """

# Add a debug endpoint to check WhatsApp API credentials
@app.route('/debug-whatsapp')
def debug_whatsapp():
    """Debug endpoint to check WhatsApp API configuration"""
    access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
    phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    
    return jsonify({
        "access_token_set": access_token is not None,
        "access_token_length": len(access_token) if access_token else 0,
        "access_token_preview": access_token[:10] + "..." if access_token and len(access_token) > 10 else access_token,
        "phone_number_id_set": phone_number_id is not None,
        "phone_number_id_length": len(phone_number_id) if phone_number_id else 0,
        "phone_number_id_preview": phone_number_id[:5] + "..." if phone_number_id and len(phone_number_id) > 5 else phone_number_id,
        "all_env_vars": {k: "SET" if v else "NOT SET" for k, v in {
            "WHATSAPP_ACCESS_TOKEN": access_token,
            "WHATSAPP_PHONE_NUMBER_ID": phone_number_id,
            "VERIFY_TOKEN": os.getenv('VERIFY_TOKEN')
        }.items()}
    })

# Add a test endpoint to check environment variables
@app.route('/test')
def test_config():
    """Test endpoint to check configuration"""
    verify_token = os.getenv('VERIFY_TOKEN')
    return jsonify({
        "verify_token_set": verify_token is not None,
        "verify_token_length": len(verify_token) if verify_token else 0,
        "verify_token_preview": verify_token[:5] + "..." if verify_token and len(verify_token) > 5 else verify_token,
        "environment_vars": list(os.environ.keys())
    })

# Add a health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "group_members": len(GROUP_MEMBERS),
        "inventory_items": len(inventory),
        "recent_updates": len(inventory_updates)
    })

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Enhanced webhook with group features"""
    
    if request.method == 'GET':
        # Webhook verification with detailed logging
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        # Debug information
        print(f"Webhook verification attempt:")
        print(f"  Mode: {mode}")
        print(f"  Token received: {token}")
        print(f"  Expected token: {os.getenv('VERIFY_TOKEN')}")
        print(f"  Challenge: {challenge}")
        
        # Check if VERIFY_TOKEN is set
        verify_token = os.getenv('VERIFY_TOKEN')
        if not verify_token:
            print("ERROR: VERIFY_TOKEN environment variable not set!")
            return "VERIFY_TOKEN not configured", 500
        
        if mode == 'subscribe' and token == verify_token:
            print("✅ Webhook verification successful!")
            return challenge
        else:
            print("❌ Webhook verification failed!")
            print(f"  Mode check: {mode == 'subscribe'}")
            print(f"  Token check: {token == verify_token}")
            return "Verification failed", 403
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            print(f"📨 Received webhook data: {json.dumps(data, indent=2)}")
            
            if 'entry' in data:
                for entry in data['entry']:
                    if 'changes' in entry:
                        for change in entry['changes']:
                            if 'value' in change and 'messages' in change['value']:
                                for message in change['value']['messages']:
                                    sender_number = message['from']
                                    message_text = message.get('text', {}).get('body', '')
                                    
                                    print(f"📱 Processing message from {sender_number}: '{message_text}'")
                                    
                                    # Process with group features
                                    response = process_group_inventory_command(message_text, sender_number)
                                    print(f"🤖 Bot response: {response}")
                                    
                                    # Send response
                                    if send_whatsapp_message(sender_number, response):
                                        print(f"✅ Response sent successfully")
                                    else:
                                        print(f"❌ Failed to send response")
            
            return "OK", 200
            
        except Exception as e:
            print(f"❌ Webhook error: {str(e)}")
            print(f"📄 Request data: {request.get_data()}")
            return f"Error: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
