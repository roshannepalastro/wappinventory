import os
import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime
import re

app = Flask(__name__)

# In-memory storage for inventory (in production, you'd use a database)
inventory = {}

# WhatsApp API configuration
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN', 'your_verify_token_here')

class InventoryManager:
    """
    This class handles all inventory operations
    Think of it as your inventory clerk who knows how to:
    - Add new items
    - Update existing quantities
    - Process sales (subtract items)
    - Generate reports
    """
    
    def __init__(self):
        self.inventory = {}
    
    def parse_inventory_message(self, message):
        """
        Parse inventory commands from WhatsApp messages
        Supports formats like:
        - apple=5, banana=12, table=10
        - sell banana=5
        - add apple=3
        """
        try:
            # Remove extra spaces and convert to lowercase for consistency
            message = message.strip().lower()
            
            # Check if it's a sell command
            if message.startswith('sell '):
                return self._parse_sell_command(message)
            
            # Check if it's an add command
            if message.startswith('add '):
                return self._parse_add_command(message)
            
            # Otherwise, treat as inventory initialization/update
            return self._parse_inventory_update(message)
            
        except Exception as e:
            return {'error': f'Could not parse message: {str(e)}'}
    
    def _parse_sell_command(self, message):
        """Parse sell commands like 'sell banana=5'"""
        # Remove 'sell ' prefix
        items_text = message[5:]
        updates = {}
        
        # Split by comma and process each item
        for item_pair in items_text.split(','):
            item_pair = item_pair.strip()
            if '=' in item_pair:
                item_name, quantity_str = item_pair.split('=', 1)
                item_name = item_name.strip()
                try:
                    quantity = int(quantity_str.strip())
                    updates[item_name] = -quantity  # Negative for selling
                except ValueError:
                    return {'error': f'Invalid quantity for {item_name}'}
        
        return {'type': 'sell', 'updates': updates}
    
    def _parse_add_command(self, message):
        """Parse add commands like 'add apple=3'"""
        # Remove 'add ' prefix
        items_text = message[4:]
        updates = {}
        
        for item_pair in items_text.split(','):
            item_pair = item_pair.strip()
            if '=' in item_pair:
                item_name, quantity_str = item_pair.split('=', 1)
                item_name = item_name.strip()
                try:
                    quantity = int(quantity_str.strip())
                    updates[item_name] = quantity
                except ValueError:
                    return {'error': f'Invalid quantity for {item_name}'}
        
        return {'type': 'add', 'updates': updates}
    
    def _parse_inventory_update(self, message):
        """Parse inventory initialization like 'apple=5, banana=12'"""
        updates = {}
        
        for item_pair in message.split(','):
            item_pair = item_pair.strip()
            if '=' in item_pair:
                item_name, quantity_str = item_pair.split('=', 1)
                item_name = item_name.strip()
                try:
                    quantity = int(quantity_str.strip())
                    updates[item_name] = quantity
                except ValueError:
                    return {'error': f'Invalid quantity for {item_name}'}
        
        return {'type': 'update', 'updates': updates}
    
    def update_inventory(self, parsed_command):
        """Update the inventory based on parsed command"""
        if 'error' in parsed_command:
            return parsed_command
        
        command_type = parsed_command['type']
        updates = parsed_command['updates']
        
        try:
            if command_type == 'update':
                # Direct update (initialization)
                for item, quantity in updates.items():
                    self.inventory[item] = quantity
            
            elif command_type == 'add':
                # Add to existing quantity
                for item, quantity in updates.items():
                    current_qty = self.inventory.get(item, 0)
                    self.inventory[item] = current_qty + quantity
            
            elif command_type == 'sell':
                # Subtract from existing quantity
                for item, quantity_change in updates.items():
                    current_qty = self.inventory.get(item, 0)
                    new_qty = current_qty + quantity_change  # quantity_change is negative
                    
                    if new_qty < 0:
                        return {'error': f'Not enough {item} in inventory (available: {current_qty})'}
                    
                    self.inventory[item] = new_qty
            
            return {'success': True, 'inventory': self.inventory.copy()}
            
        except Exception as e:
            return {'error': f'Failed to update inventory: {str(e)}'}
    
    def get_inventory_display(self):
        """Generate a formatted inventory display"""
        if not self.inventory:
            return "📦 Inventory is empty"
        
        display = "📦 **Current Inventory**\n"
        display += "─" * 25 + "\n"
        
        for item, quantity in sorted(self.inventory.items()):
            display += f"{item.title()}: {quantity}\n"
        
        display += "─" * 25 + "\n"
        display += f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return display

# Initialize inventory manager
inventory_manager = InventoryManager()

def send_whatsapp_message(phone_number, message):
    """
    Send a message back to WhatsApp
    This is like having a postal service for your bot
    """
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        print("WhatsApp credentials not configured")
        return False
    
    url = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": message}
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """
    WhatsApp webhook verification
    This is like proving your identity to WhatsApp
    """
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        print("Webhook verified successfully!")
        return challenge
    else:
        print("Webhook verification failed!")
        return 'Forbidden', 403

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """
    Handle incoming WhatsApp messages
    This is the main brain of your bot
    """
    try:
        data = request.get_json()
        
        # Check if this is a message event
        if 'entry' in data:
            for entry in data['entry']:
                if 'changes' in entry:
                    for change in entry['changes']:
                        if 'value' in change and 'messages' in change['value']:
                            for message in change['value']['messages']:
                                # Extract message details
                                phone_number = message['from']
                                message_text = message.get('text', {}).get('body', '')
                                
                                print(f"Received message from {phone_number}: {message_text}")
                                
                                # Process the inventory command
                                response = process_inventory_command(message_text)
                                
                                # Send response back to WhatsApp
                                send_whatsapp_message(phone_number, response)
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"Error handling webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def process_inventory_command(message_text):
    """
    Process inventory commands and return appropriate response
    This is where the magic happens - converting chat messages to inventory actions
    """
    # Handle help command
    if message_text.lower().strip() in ['help', '/help', '?']:
        return """🤖 **Inventory Bot Help**

**Commands:**
• Initialize inventory: `apple=5, banana=12, table=10`
• Sell items: `sell banana=5`
• Add items: `add apple=3`
• View inventory: `inventory` or `show`
• Help: `help`

**Example:**
User: `apple=10, banana=5`
Bot: Updates inventory

User: `sell apple=2`
Bot: Reduces apple count by 2

User: `inventory`
Bot: Shows current inventory"""
    
    # Handle inventory display command
    if message_text.lower().strip() in ['inventory', 'show', 'status']:
        return inventory_manager.get_inventory_display()
    
    # Parse and process inventory command
    parsed_command = inventory_manager.parse_inventory_message(message_text)
    
    if 'error' in parsed_command:
        return f"❌ Error: {parsed_command['error']}\n\nSend 'help' for usage instructions."
    
    # Update inventory
    result = inventory_manager.update_inventory(parsed_command)
    
    if 'error' in result:
        return f"❌ Error: {result['error']}"
    
    # Generate success response
    command_type = parsed_command['type']
    updates = parsed_command['updates']
    
    if command_type == 'sell':
        response = "✅ **Sale Recorded!**\n"
        for item, quantity_change in updates.items():
            response += f"Sold {abs(quantity_change)} {item.title()}\n"
    elif command_type == 'add':
        response = "✅ **Items Added!**\n"
        for item, quantity in updates.items():
            response += f"Added {quantity} {item.title()}\n"
    else:
        response = "✅ **Inventory Updated!**\n"
    
    response += "\n" + inventory_manager.get_inventory_display()
    
    return response

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'inventory_items': len(inventory_manager.inventory)
    })

@app.route('/', methods=['GET'])
def home():
    """Simple home page"""
    return """
    <h1>WhatsApp Inventory Management System</h1>
    <p>Bot is running and ready to receive messages!</p>
    <p>Current inventory items: {}</p>
    <p>Send messages to your WhatsApp number to interact with the bot.</p>
    """.format(len(inventory_manager.inventory))

if __name__ == '__main__':
    # For development
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))