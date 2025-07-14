# app.py - Main Flask Application
import os
import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Global inventory storage (in production, use a database)
inventory = {}
transaction_history = []

class InventoryManager:
    """Handles all inventory operations like add, sell, and initialize"""
    
    def __init__(self):
        self.inventory = inventory
        self.history = transaction_history
    
    def process_command(self, message_text, user_name):
        """
        Process inventory commands from WhatsApp messages
        Returns: (success, response_message)
        """
        message_text = message_text.strip().lower()
        
        # Help command
        if message_text in ['help', '/help']:
            return True, self.get_help_message()
        
        # Show inventory command
        if message_text in ['inventory', 'show', 'status']:
            return True, self.format_inventory()
        
        # Check for sell command
        if message_text.startswith('sell '):
            return self.handle_sell(message_text, user_name)
        
        # Check for add command
        if message_text.startswith('add '):
            return self.handle_add(message_text, user_name)
        
        # Check for initialization (item=quantity format)
        if '=' in message_text and not message_text.startswith(('sell ', 'add ')):
            return self.handle_initialize(message_text, user_name)
        
        # Unknown command
        return False, f"❌ Unknown command. Send 'help' for available commands."
    
    def handle_sell(self, message_text, user_name):
        """Handle sell commands like 'sell banana=5'"""
        try:
            # Remove 'sell ' prefix
            items_text = message_text[5:].strip()
            items = self.parse_items(items_text)
            
            if not items:
                return False, "❌ Invalid format. Use: sell item=quantity"
            
            # Check if all items are available
            for item, quantity in items.items():
                if item not in self.inventory:
                    return False, f"❌ {item} not found in inventory"
                if self.inventory[item] < quantity:
                    return False, f"❌ Not enough {item}. Available: {self.inventory[item]}"
            
            # Process the sale
            for item, quantity in items.items():
                self.inventory[item] -= quantity
                self.add_to_history('sell', item, quantity, user_name)
            
            return True, f"✅ Sale recorded by {user_name}\n\n{self.format_inventory()}"
            
        except Exception as e:
            return False, f"❌ Error processing sale: {str(e)}"
    
    def handle_add(self, message_text, user_name):
        """Handle add commands like 'add apple=3'"""
        try:
            # Remove 'add ' prefix
            items_text = message_text[4:].strip()
            items = self.parse_items(items_text)
            
            if not items:
                return False, "❌ Invalid format. Use: add item=quantity"
            
            # Add items to inventory
            for item, quantity in items.items():
                if item in self.inventory:
                    self.inventory[item] += quantity
                else:
                    self.inventory[item] = quantity
                self.add_to_history('add', item, quantity, user_name)
            
            return True, f"✅ Items added by {user_name}\n\n{self.format_inventory()}"
            
        except Exception as e:
            return False, f"❌ Error adding items: {str(e)}"
    
    def handle_initialize(self, message_text, user_name):
        """Handle initialization like 'apple=5, banana=12'"""
        try:
            items = self.parse_items(message_text)
            
            if not items:
                return False, "❌ Invalid format. Use: item=quantity, item2=quantity2"
            
            # Initialize inventory
            for item, quantity in items.items():
                self.inventory[item] = quantity
                self.add_to_history('initialize', item, quantity, user_name)
            
            return True, f"✅ Inventory initialized by {user_name}\n\n{self.format_inventory()}"
            
        except Exception as e:
            return False, f"❌ Error initializing inventory: {str(e)}"
    
    def parse_items(self, text):
        """Parse item=quantity pairs from text"""
        items = {}
        # Split by comma and process each item
        for item_pair in text.split(','):
            item_pair = item_pair.strip()
            if '=' in item_pair:
                try:
                    item, quantity = item_pair.split('=', 1)
                    item = item.strip()
                    quantity = int(quantity.strip())
                    if quantity < 0:
                        continue
                    items[item] = quantity
                except ValueError:
                    continue
        return items
    
    def format_inventory(self):
        """Format inventory for display"""
        if not self.inventory:
            return "📦 Inventory is empty"
        
        lines = ["📦 Current Inventory:", "=" * 20]
        for item, quantity in sorted(self.inventory.items()):
            lines.append(f"{item}: {quantity}")
        
        return "\n".join(lines)
    
    def add_to_history(self, action, item, quantity, user):
        """Add transaction to history"""
        self.history.append({
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'item': item,
            'quantity': quantity,
            'user': user
        })
    
    def get_help_message(self):
        """Return help message"""
        return """📋 Inventory Bot Commands:

🆕 Initialize inventory:
   apple=5, banana=12

➕ Add items:
   add apple=3

➖ Sell items:
   sell banana=5

📦 Show inventory:
   inventory

❓ Show help:
   help"""

# Create inventory manager instance
inventory_manager = InventoryManager()

def send_whatsapp_message(phone_number, message):
    """Send message back to WhatsApp"""
    url = f"https://graph.facebook.com/v18.0/{os.getenv('WHATSAPP_PHONE_NUMBER_ID')}/messages"
    
    headers = {
        'Authorization': f'Bearer {os.getenv("WHATSAPP_TOKEN")}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'messaging_product': 'whatsapp',
        'to': phone_number,
        'type': 'text',
        'text': {'body': message}
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

@app.route('/')
def home():
    """Home page to verify app is running"""
    return {
        'status': 'WhatsApp Inventory Bot Running',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0'
    }

@app.route('/health')
def health():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'inventory_items': len(inventory)
    }

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """WhatsApp webhook endpoint"""
    
    if request.method == 'GET':
        # Webhook verification
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        print(f"Verification - Mode: {mode}, Token: {token}")
        print(f"Expected token: {os.getenv('VERIFY_TOKEN')}")
        
        # If no parameters, show helpful message
        if not mode and not token and not challenge:
            return {
                'error': 'This is a WhatsApp webhook endpoint',
                'message': 'Access forbidden - requires WhatsApp verification parameters',
                'test_url': f'Add these parameters: ?hub.mode=subscribe&hub.verify_token={os.getenv("VERIFY_TOKEN")}&hub.challenge=test123'
            }, 403
        
        if mode == 'subscribe' and token == os.getenv('VERIFY_TOKEN'):
            print("✅ Webhook verification successful!")
            return challenge
        else:
            print("❌ Webhook verification failed!")
            return 'Verification failed', 403
    
    elif request.method == 'POST':
        # Handle incoming messages
        try:
            body = request.get_json()
            print(f"Received webhook: {json.dumps(body, indent=2)}")
            
            # Extract message data
            if 'entry' in body:
                for entry in body['entry']:
                    if 'changes' in entry:
                        for change in entry['changes']:
                            if 'value' in change and 'messages' in change['value']:
                                messages = change['value']['messages']
                                contacts = change['value'].get('contacts', [])
                                
                                for message in messages:
                                    if message.get('type') == 'text':
                                        phone_number = message['from']
                                        message_text = message['text']['body']
                                        
                                        # Get user name
                                        user_name = phone_number  # Default to phone number
                                        for contact in contacts:
                                            if contact['wa_id'] == phone_number:
                                                user_name = contact.get('profile', {}).get('name', phone_number)
                                                break
                                        
                                        print(f"Processing message from {user_name}: {message_text}")
                                        
                                        # Process the inventory command
                                        success, response = inventory_manager.process_command(message_text, user_name)
                                        
                                        # Send response back to WhatsApp
                                        if send_whatsapp_message(phone_number, response):
                                            print(f"✅ Response sent to {user_name}")
                                        else:
                                            print(f"❌ Failed to send response to {user_name}")
            
            return 'OK', 200
            
        except Exception as e:
            print(f"Error processing webhook: {e}")
            return 'Error', 500

@app.route('/debug')
def debug():
    """Debug endpoint to check configuration"""
    return {
        'verify_token': os.getenv('VERIFY_TOKEN'),
        'whatsapp_token': os.getenv('WHATSAPP_TOKEN')[:10] + '...' if os.getenv('WHATSAPP_TOKEN') else 'Not set',
        'phone_number_id': os.getenv('WHATSAPP_PHONE_NUMBER_ID'),
        'inventory_count': len(inventory),
        'current_inventory': inventory
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
