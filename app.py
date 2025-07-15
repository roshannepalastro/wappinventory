# group_admin_bot.py - Enhanced with Firebase Firestore Support
import os
import json
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify
from datetime import datetime
import logging

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Group admin configuration
GROUP_ADMINS = {
    "9779816034951": "Admin User 1",  # Your number
    # Add more admin numbers here
}

# Initialize Firebase
db = None


# Enhanced Firebase initialization with better error reporting
def init_firebase():
    """Initialize Firebase connection with detailed error reporting"""
    global db
    try:
        logger.info("Initializing Firebase...")
        
        # Check for Firebase credentials
        firebase_creds = os.getenv('FIREBASE_CREDENTIALS')
        
        if firebase_creds:
            logger.info("Using Firebase credentials from environment variable")
            try:
                cred_dict = json.loads(firebase_creds)
                cred = credentials.Certificate(cred_dict)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in FIREBASE_CREDENTIALS: {str(e)}")
                return False
        else:
            logger.info("Using Firebase credentials from file")
            if not os.path.exists('firebase-service-account.json'):
                logger.error("Firebase service account file not found")
                return False
            cred = credentials.Certificate('firebase-service-account.json')
        
        # Initialize Firebase app
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
            logger.info("Firebase app initialized")
        else:
            logger.info("Firebase app already initialized")
        
        # Initialize Firestore client
        db = firestore.client()
        
        # Test the connection
        test_doc = db.collection('_test').document('connection_test')
        test_doc.set({'test': True, 'timestamp': firestore.SERVER_TIMESTAMP})
        test_doc.delete()  # Clean up
        
        logger.info("Firebase initialized and tested successfully")
        return True
        
    except Exception as e:
        logger.error(f"Firebase initialization error: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        return False

# Firebase Database Manager
# Enhanced Firebase Manager with detailed error logging
class FirebaseManager:
    @staticmethod
    def add_group_member(phone_number, name=None):
        """Add member to group with enhanced error handling"""
        if not db:
            logger.error("Firebase database not initialized")
            return False, "Database not initialized"
        
        try:
            member_data = {
                'phone_number': phone_number,
                'name': name or f"User {phone_number[-4:]}",
                'joined_at': firestore.SERVER_TIMESTAMP,
                'is_active': True
            }
            
            # Use phone number as document ID for easy lookup
            doc_ref = db.collection('group_members').document(phone_number)
            doc_ref.set(member_data)
            
            logger.info(f"Successfully added group member: {phone_number}")
            return True, "Success"
            
        except Exception as e:
            error_msg = f"Error adding group member: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    @staticmethod
    def is_group_member(phone_number):
        """Check if user is active group member with enhanced error handling"""
        if not db:
            logger.error("Firebase database not initialized")
            return False
        
        try:
            doc_ref = db.collection('group_members').document(phone_number)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                is_active = data.get('is_active', False)
                logger.info(f"User {phone_number} membership status: {is_active}")
                return is_active
            
            logger.info(f"User {phone_number} not found in group members")
            return False
            
        except Exception as e:
            logger.error(f"Error checking group membership: {str(e)}")
            return False
    
    @staticmethod
    def remove_group_member(phone_number):
        """Remove member from group"""
        if not db:
            return False
        
        try:
            db.collection('group_members').document(phone_number).update({
                'is_active': False,
                'left_at': firestore.SERVER_TIMESTAMP
            })
            logger.info(f"Removed group member: {phone_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing group member: {str(e)}")
            return False
    
    @staticmethod
    def get_group_members():
        """Get all active group members"""
        if not db:
            return []
        
        try:
            members_ref = db.collection('group_members')
            query = members_ref.where('is_active', '==', True)
            docs = query.stream()
            
            members = []
            for doc in docs:
                member_data = doc.to_dict()
                members.append({
                    'phone_number': member_data['phone_number'],
                    'name': member_data['name']
                })
            
            return members
            
        except Exception as e:
            logger.error(f"Error getting group members: {str(e)}")
            return []
    
    
    @staticmethod
    def update_inventory(item_name, quantity):
        """Update inventory item"""
        if not db:
            return False
        
        try:
            inventory_data = {
                'item_name': item_name,
                'quantity': quantity,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            # Use item name as document ID
            db.collection('inventory').document(item_name).set(inventory_data)
            logger.info(f"Updated inventory: {item_name} = {quantity}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating inventory: {str(e)}")
            return False
    
    @staticmethod
    def get_inventory():
        """Get current inventory"""
        if not db:
            return {}
        
        try:
            inventory_ref = db.collection('inventory')
            docs = inventory_ref.stream()
            
            inventory = {}
            for doc in docs:
                data = doc.to_dict()
                if data['quantity'] > 0:
                    inventory[data['item_name']] = data['quantity']
            
            return inventory
            
        except Exception as e:
            logger.error(f"Error getting inventory: {str(e)}")
            return {}
    
    @staticmethod
    def get_inventory_item(item_name):
        """Get specific inventory item"""
        if not db:
            return 0
        
        try:
            doc_ref = db.collection('inventory').document(item_name)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return data.get('quantity', 0)
            return 0
            
        except Exception as e:
            logger.error(f"Error getting inventory item: {str(e)}")
            return 0
    
    @staticmethod
    def add_inventory_update(user_phone, user_name, action, item_name=None, quantity=None, description=None):
        """Log inventory update"""
        if not db:
            return False
        
        try:
            update_data = {
                'user_phone': user_phone,
                'user_name': user_name,
                'action': action,
                'item_name': item_name,
                'quantity': quantity,
                'description': description,
                'timestamp': firestore.SERVER_TIMESTAMP
            }
            
            db.collection('inventory_updates').add(update_data)
            logger.info(f"Logged update: {user_name} - {action}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding inventory update: {str(e)}")
            return False
    
    @staticmethod
    def get_recent_updates(limit=10):
        """Get recent inventory updates"""
        if not db:
            return []
        
        try:
            updates_ref = db.collection('inventory_updates')
            query = updates_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
            docs = query.stream()
            
            updates = []
            for doc in docs:
                data = doc.to_dict()
                updates.append(data)
            
            return updates
            
        except Exception as e:
            logger.error(f"Error getting recent updates: {str(e)}")
            return []
    
    @staticmethod
    def clear_inventory():
        """Clear all inventory"""
        if not db:
            return False
        
        try:
            # Get all inventory documents
            inventory_ref = db.collection('inventory')
            docs = inventory_ref.stream()
            
            # Delete each document
            for doc in docs:
                doc.reference.delete()
            
            logger.info("Cleared all inventory")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing inventory: {str(e)}")
            return False
    
    @staticmethod
    def delete_inventory_item(item_name):
        """Delete specific inventory item"""
        if not db:
            return False
        
        try:
            db.collection('inventory').document(item_name).delete()
            logger.info(f"Deleted inventory item: {item_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting inventory item: {str(e)}")
            return False

def is_group_admin(phone_number):
    """Check if user is group admin"""
    return phone_number in GROUP_ADMINS

def send_whatsapp_message(to_number, message):
    """Send WhatsApp message using Graph API"""
    try:
        access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        
        if not access_token or not phone_number_id:
            logger.error("WhatsApp API credentials not configured")
            return False
        
        url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
        
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
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            logger.info(f"Message sent successfully to {to_number}")
            return True
        else:
            logger.error(f"Failed to send message: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return False

def broadcast_to_group(message, exclude_number=None):
    """Send message to all group members"""
    members = FirebaseManager.get_group_members()
    sent_count = 0
    
    for member in members:
        if member['phone_number'] != exclude_number:
            if send_whatsapp_message(member['phone_number'], message):
                sent_count += 1
    
    return sent_count

# Enhanced join command with better error handling
def process_group_inventory_command(message_text, sender_number):
    """Process inventory commands with enhanced error handling"""
    
    message_text = message_text.lower().strip()
    sender_name = GROUP_ADMINS.get(sender_number, f"User {sender_number[-4:]}")
    
    # Join group command with enhanced error handling
    if message_text == "join":
        logger.info(f"Processing join command from {sender_number}")
        
        # Check if Firebase is initialized
        if not db:
            logger.error("Firebase not initialized")
            return "❌ System error: Database not available. Please contact admin."
        
        # Check current membership status
        is_member = FirebaseManager.is_group_member(sender_number)
        logger.info(f"Current membership status for {sender_number}: {is_member}")
        
        if not is_member:
            # Attempt to add member
            success, error_msg = FirebaseManager.add_group_member(sender_number, sender_name)
            
            if success:
                try:
                    members = FirebaseManager.get_group_members()
                    response = f"✅ {sender_name} joined the inventory group!\n"
                    response += f"👥 Total members: {len(members)}\n"
                    response += "Type 'help' for commands."
                    
                    # Notify other members
                    broadcast_message = f"👋 {sender_name} joined the inventory group!"
                    broadcast_to_group(broadcast_message, exclude_number=sender_number)
                    
                    # Log the action
                    FirebaseManager.add_inventory_update(
                        sender_number, sender_name, "join", 
                        description="Joined the group"
                    )
                    
                    logger.info(f"Successfully processed join for {sender_number}")
                    return response
                    
                except Exception as e:
                    logger.error(f"Error in post-join processing: {str(e)}")
                    return "✅ Joined successfully, but some features may be limited."
            else:
                logger.error(f"Failed to add member {sender_number}: {error_msg}")
                return f"❌ Error joining group: {error_msg}"
        else:
            logger.info(f"User {sender_number} already in group")
            return "✅ You're already in the group!"
    
    
    # Leave group command
    elif message_text == "leave":
        if FirebaseManager.is_group_member(sender_number):
            if FirebaseManager.remove_group_member(sender_number):
                broadcast_message = f"👋 {sender_name} left the inventory group"
                broadcast_to_group(broadcast_message, exclude_number=sender_number)
                
                # Log the action
                FirebaseManager.add_inventory_update(
                    sender_number, sender_name, "leave", 
                    description="Left the group"
                )
                
                return "✅ You left the inventory group"
            else:
                return "❌ Error leaving group. Please try again."
        else:
            return "❌ You're not in the group"
    
    # Check if user is in group
    if not FirebaseManager.is_group_member(sender_number):
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
• remove apple - Remove item completely (admin only)

💡 *Examples:*
• apple=10, banana=5, orange=8
• add apple=5
• sell banana=3"""
        return response
    
    # Show group members
    elif message_text == "members":
        members = FirebaseManager.get_group_members()
        if not members:
            return "👥 No members in the group"
        
        response = f"👥 *Group Members ({len(members)}):*\n"
        for i, member in enumerate(members, 1):
            member_name = member['name']
            admin_badge = " 👑" if is_group_admin(member['phone_number']) else ""
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
        
        # Log the action
        FirebaseManager.add_inventory_update(
            sender_number, sender_name, "broadcast", 
            description=f"Broadcast message to {sent_count} members"
        )
        
        return f"✅ Message sent to {sent_count} members"
    
    # Reset inventory (admin only)
    elif message_text == "reset":
        if not is_group_admin(sender_number):
            return "❌ Only admins can reset inventory"
        
        if FirebaseManager.clear_inventory():
            # Notify group
            broadcast_message = f"🔄 {sender_name} reset the inventory"
            broadcast_to_group(broadcast_message, exclude_number=sender_number)
            
            # Log the action
            FirebaseManager.add_inventory_update(
                sender_number, sender_name, "reset", 
                description="Reset all inventory"
            )
            
            return "✅ Inventory reset successfully"
        else:
            return "❌ Error resetting inventory"
    
    # Remove specific item (admin only)
    elif message_text.startswith("remove "):
        if not is_group_admin(sender_number):
            return "❌ Only admins can remove items"
        
        item_name = message_text[7:].strip()
        if not item_name:
            return "❌ Usage: remove apple"
        
        if FirebaseManager.get_inventory_item(item_name) > 0:
            if FirebaseManager.delete_inventory_item(item_name):
                # Log the action
                FirebaseManager.add_inventory_update(
                    sender_number, sender_name, "remove", 
                    item_name, description=f"Removed {item_name} from inventory"
                )
                
                # Notify group
                broadcast_message = f"🗑️ {sender_name} removed {item_name} from inventory"
                broadcast_to_group(broadcast_message, exclude_number=sender_number)
                
                return f"✅ Removed {item_name} from inventory"
            else:
                return "❌ Error removing item"
        else:
            return f"❌ {item_name} not found in inventory"
    
    # Show inventory
    elif message_text == "inventory":
        inventory = FirebaseManager.get_inventory()
        if not inventory:
            return "📦 Inventory is empty"
        
        response = "📦 *Current Inventory:*\n"
        total_items = 0
        for item, quantity in sorted(inventory.items()):
            response += f"• {item}: {quantity}\n"
            total_items += quantity
        
        response += f"\n📊 Total items: {total_items}"
        return response
    
    # Show update history
    elif message_text == "history":
        updates = FirebaseManager.get_recent_updates(8)
        if not updates:
            return "📋 No inventory updates yet"
        
        response = "📋 *Recent Updates:*\n"
        for update in updates:
            time_str = ""
            if update.get('timestamp'):
                # Handle Firestore timestamp
                timestamp = update['timestamp']
                if hasattr(timestamp, 'timestamp'):
                    dt = datetime.fromtimestamp(timestamp.timestamp())
                    time_str = dt.strftime('%H:%M')
                else:
                    time_str = "now"
            
            response += f"• {update['user_name']} {update['action']}"
            if update.get('item_name'):
                response += f" {update['item_name']}"
            if update.get('quantity'):
                response += f" ({update['quantity']})"
            if time_str:
                response += f" at {time_str}"
            response += "\n"
        
        return response
    
    # Add items
    elif message_text.startswith("add "):
        try:
            item_data = message_text[4:].strip()
            if "=" in item_data:
                item, quantity = item_data.split("=", 1)
                item = item.strip()
                quantity = int(quantity.strip())
                
                if quantity <= 0:
                    return "❌ Quantity must be positive"
                
                current_quantity = FirebaseManager.get_inventory_item(item)
                new_quantity = current_quantity + quantity
                
                if FirebaseManager.update_inventory(item, new_quantity):
                    # Log update
                    FirebaseManager.add_inventory_update(
                        sender_number, sender_name, "add", 
                        item, quantity, f"Added {quantity} {item}(s)"
                    )
                    
                    response = f"✅ Added {quantity} {item}(s)\n"
                    response += f"📦 New quantity: {new_quantity}"
                    
                    # Notify group
                    broadcast_message = f"➕ {sender_name} added {quantity} {item}(s) to inventory"
                    broadcast_to_group(broadcast_message, exclude_number=sender_number)
                    
                    return response
                else:
                    return "❌ Error updating inventory"
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
                
                if quantity <= 0:
                    return "❌ Quantity must be positive"
                
                current_quantity = FirebaseManager.get_inventory_item(item)
                
                if current_quantity == 0:
                    return f"❌ {item} not found in inventory"
                
                if current_quantity < quantity:
                    return f"❌ Not enough {item}. Available: {current_quantity}"
                
                new_quantity = current_quantity - quantity
                
                if new_quantity == 0:
                    # Remove item if quantity becomes 0
                    FirebaseManager.delete_inventory_item(item)
                else:
                    FirebaseManager.update_inventory(item, new_quantity)
                
                # Log update
                FirebaseManager.add_inventory_update(
                    sender_number, sender_name, "sell", 
                    item, quantity, f"Sold {quantity} {item}(s)"
                )
                
                response = f"✅ Sold {quantity} {item}(s)\n"
                response += f"📦 Remaining: {new_quantity}"
                
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
                    
                    if quantity < 0:
                        return f"❌ Quantity for {name} must be non-negative"
                    
                    if quantity == 0:
                        # Remove item if quantity is 0
                        if FirebaseManager.get_inventory_item(name) > 0:
                            FirebaseManager.delete_inventory_item(name)
                            updated_items.append(f"{name}: removed")
                    else:
                        if FirebaseManager.update_inventory(name, quantity):
                            updated_items.append(f"{name}: {quantity}")
            
            if updated_items:
                # Log update
                FirebaseManager.add_inventory_update(
                    sender_number, sender_name, "update", 
                    description="Updated inventory items"
                )
                
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

# Routes
@app.route('/')
def home():
    """Landing page for the inventory bot"""
    try:
        if not db:
            return """
            <html>
            <body>
                <h1>🤖 WhatsApp Inventory Bot</h1>
                <div style="background: #ffe8e8; padding: 10px; border-radius: 5px; margin: 20px 0; color: #d32f2f;">
                    <strong>❌ Firebase Error:</strong> Database not initialized
                </div>
                <p>Please check your Firebase configuration.</p>
            </body>
            </html>
            """
        
        members = FirebaseManager.get_group_members()
        inventory = FirebaseManager.get_inventory()
        updates = FirebaseManager.get_recent_updates(5)
        
        group_count = len(members)
        inventory_count = len(inventory)
        updates_count = len(updates)
        webhook_url = f"{request.host_url}webhook"
        
        return f"""
        <html>
        <head>
            <title>WhatsApp Inventory Bot</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
                h1 {{ color: #25d366; }}
                .status {{ background: #e8f5e8; padding: 10px; border-radius: 5px; margin: 20px 0; }}
                .firebase {{ background: #fff3e0; padding: 10px; border-radius: 5px; margin: 20px 0; color: #f57c00; }}
                .command {{ background: #f0f0f0; padding: 5px; margin: 5px 0; font-family: monospace; }}
            </style>
        </head>
        <body>
            <h1>🤖 WhatsApp Inventory Bot</h1>
            
            <div class="status">
                <strong>✅ Bot Status:</strong> Online with Firebase Storage
            </div>
            
            <div class="firebase">
                <strong>🔥 Firebase:</strong> Connected and Ready
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
            <div class="command">remove apple</div>
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
    except Exception as e:
        return f"""
        <html>
        <body>
            <h1>🤖 WhatsApp Inventory Bot</h1>
            <div style="background: #ffe8e8; padding: 10px; border-radius: 5px; margin: 20px 0; color: #d32f2f;">
                <strong>❌ Firebase Error:</strong> {str(e)}
            </div>
            <p>Please check your Firebase configuration.</p>
        </body>
        </html>
        """

@app.route('/firebase-status')
def firebase_status():
    """Check Firebase connection status"""
    return jsonify({
        "firebase_connected": db is not None,
        "timestamp": datetime.now().isoformat()
    })

# Enhanced webhook with better error handling
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Enhanced webhook with better error handling"""
    
    if request.method == 'GET':
        # Webhook verification (unchanged)
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        verify_token = os.getenv('VERIFY_TOKEN')
        if not verify_token:
            logger.error("VERIFY_TOKEN not configured")
            return "VERIFY_TOKEN not configured", 500
        
        if mode == 'subscribe' and token == verify_token:
            logger.info("Webhook verification successful")
            return challenge
        else:
            logger.error("Webhook verification failed")
            return "Verification failed", 403
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            logger.info(f"Received webhook data: {json.dumps(data, indent=2)}")
            
            # Check Firebase status before processing
            if not db:
                logger.error("Firebase not initialized - cannot process messages")
                return "Firebase not available", 500
            
            if 'entry' in data:
                for entry in data['entry']:
                    if 'changes' in entry:
                        for change in entry['changes']:
                            if 'value' in change and 'messages' in change['value']:
                                for message in change['value']['messages']:
                                    sender_number = message['from']
                                    message_text = message.get('text', {}).get('body', '')
                                    
                                    logger.info(f"Processing message from {sender_number}: '{message_text}'")
                                    
                                    try:
                                        # Process with enhanced error handling
                                        response = process_group_inventory_command(message_text, sender_number)
                                        logger.info(f"Bot response: {response}")
                                        
                                        # Send response
                                        if send_whatsapp_message(sender_number, response):
                                            logger.info("Response sent successfully")
                                        else:
                                            logger.error("Failed to send response")
                                            
                                    except Exception as msg_error:
                                        logger.error(f"Error processing message: {str(msg_error)}")
                                        # Send error message to user
                                        error_response = "❌ System error occurred. Please try again or contact admin."
                                        send_whatsapp_message(sender_number, error_response)
            
            return "OK", 200
            
        except Exception as e:
            logger.error(f"Webhook error: {str(e)}")
            return f"Error: {str(e)}", 500

if __name__ == '__main__':
    # Initialize Firebase
    if init_firebase():
        logger.info("Starting Flask app with Firebase support")
    else:
        logger.error("Failed to initialize Firebase - app may not work properly")
    
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
