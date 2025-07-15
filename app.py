import os
import json
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Database connection with psycopg2
def get_db_connection():
    """Get database connection with psycopg2"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            port=os.getenv('DB_PORT', 5432),
            sslmode='require'
        )
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None


def test_database_connection():
    """Test database connection on startup"""
    conn = get_db_connection()
    if conn:
        print("✅ Database connection successful")
        conn.close()
        return True
    else:
        print("❌ Database connection failed")
        return False

# Test connection on startup
if not test_database_connection():
    print("⚠️  Warning: Database connection failed. Please check your environment variables.")

def init_database():
    """Initialize database tables"""
    conn = get_db_connection()
    if not conn:
        print("❌ Cannot initialize database - no connection")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Create members table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS members (
                phone_number VARCHAR(20) PRIMARY KEY,
                name VARCHAR(100),
                joined_date TIMESTAMP,
                is_admin BOOLEAN DEFAULT FALSE,
                message_count INTEGER DEFAULT 0,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create inventory table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                item_name VARCHAR(100) PRIMARY KEY,
                quantity INTEGER NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create activity log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_log (
                id SERIAL PRIMARY KEY,
                phone_number VARCHAR(20),
                action VARCHAR(50),
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        print("✅ Database tables initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

# Initialize database on startup
init_database()

# Group admin configuration
GROUP_ADMINS = {
    "9779816034951": "Admin User 1",
    # Add more admins here
}

def is_admin(phone_number):
    return phone_number in GROUP_ADMINS

def add_or_update_member(phone_number):
    """Add new member or update existing member's activity"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check if member exists
        cursor.execute('SELECT phone_number FROM members WHERE phone_number = %s', (phone_number,))
        exists = cursor.fetchone()
        
        if not exists:
            # Add new member
            cursor.execute('''
                INSERT INTO members (phone_number, name, joined_date, is_admin, message_count, last_activity)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (
                phone_number,
                f"User {phone_number}",
                datetime.now(),
                is_admin(phone_number),
                1,
                datetime.now()
            ))
            print(f"➕ New member added: {phone_number}")
            
            # Log activity
            cursor.execute('''
                INSERT INTO activity_log (phone_number, action, details)
                VALUES (%s, %s, %s)
            ''', (phone_number, 'joined', 'New member joined the group'))
            
        else:
            # Update existing member
            cursor.execute('''
                UPDATE members 
                SET message_count = message_count + 1, last_activity = %s
                WHERE phone_number = %s
            ''', (datetime.now(), phone_number))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ Error updating member: {e}")
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_all_members():
    """Get all members from database"""
    conn = get_db_connection()
    if not conn:
        return {}
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM members ORDER BY joined_date')
        members = cursor.fetchall()
        
        # Convert to dictionary format
        result = {}
        for member in members:
            result[member['phone_number']] = {
                'name': member['name'],
                'joined_date': member['joined_date'].isoformat(),
                'is_admin': member['is_admin'],
                'message_count': member['message_count'],
                'last_activity': member['last_activity'].isoformat()
            }
        
        return result
        
    except Exception as e:
        print(f"❌ Error getting members: {e}")
        return {}
    finally:
        if conn:
            conn.close()

def update_inventory(item, quantity):
    """Update inventory in database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        if quantity <= 0:
            # Remove item
            cursor.execute('DELETE FROM inventory WHERE item_name = %s', (item,))
        else:
            # Update or insert item using psycopg2 syntax
            cursor.execute('''
                INSERT INTO inventory (item_name, quantity, last_updated)
                VALUES (%s, %s, %s)
                ON CONFLICT (item_name) 
                DO UPDATE SET quantity = EXCLUDED.quantity, last_updated = EXCLUDED.last_updated
            ''', (item, quantity, datetime.now()))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ Error updating inventory: {e}")
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_inventory():
    """Get all inventory items from database"""
    conn = get_db_connection()
    if not conn:
        return {}
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM inventory ORDER BY item_name')
        items = cursor.fetchall()
        
        # Convert to dictionary format
        result = {}
        for item in items:
            result[item['item_name']] = item['quantity']
        
        return result
        
    except Exception as e:
        print(f"❌ Error getting inventory: {e}")
        return {}
    finally:
        if conn:
            conn.close()

def remove_member(phone_number):
    """Remove member from database"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM members WHERE phone_number = %s', (phone_number,))
        
        # Log activity
        cursor.execute('''
            INSERT INTO activity_log (phone_number, action, details)
            VALUES (%s, %s, %s)
        ''', (phone_number, 'kicked', 'Member removed from group'))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ Error removing member: {e}")
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def clear_inventory():
    """Clear all inventory items"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM inventory')
        
        # Log activity
        cursor.execute('''
            INSERT INTO activity_log (phone_number, action, details)
            VALUES (%s, %s, %s)
        ''', ('system', 'reset', 'Inventory cleared by admin'))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ Error clearing inventory: {e}")
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def send_whatsapp_message(phone_number, message):
    """Send message via WhatsApp Business API"""
    access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
    phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
    
    if not access_token or not phone_number_id:
        print("❌ WhatsApp API credentials not configured!")
        return False
    
    url = f"https://graph.facebook.com/v17.0/{phone_number_id}/messages"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    data = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": message}
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            print(f"✅ Message sent successfully to {phone_number}")
            return True
        else:
            print(f"❌ Failed to send message: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False

@app.route('/')
def home():
    members = get_all_members()
    inventory = get_inventory()
    
    member_count = len(members)
    inventory_count = len(inventory)
    last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>WhatsApp Inventory Bot - Database Storage</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #25D366; text-align: center; }}
            .status {{ background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .commands {{ background: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .commands h3 {{ margin-top: 0; }}
            .stat {{ display: inline-block; margin: 10px 15px; padding: 10px; background: #e3f2fd; border-radius: 5px; }}
            .persistent {{ background: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; border: 1px solid #c3e6cb; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📱 WhatsApp Inventory Bot</h1>
            
            <div class="status">
                <h3>🟢 Bot Status: Online</h3>
                <div class="stat">👥 Members: {member_count}</div>
                <div class="stat">📦 Inventory Items: {inventory_count}</div>
                <div class="stat">🔄 Last Update: {last_update}</div>
            </div>
            
            <div class="persistent">
                <h3>🔒 Data Protection: PERMANENT STORAGE</h3>
                <p>✅ <strong>Database Storage:</strong> All data is stored in PostgreSQL database</p>
                <p>✅ <strong>Survives Restarts:</strong> Data persists through server restarts</p>
                <p>✅ <strong>Survives Redeployment:</strong> Data persists even if you redeploy the app</p>
                <p>✅ <strong>Backup Available:</strong> Database can be backed up independently</p>
                <p>⚠️ <strong>Only lost if:</strong> Database itself is deleted (requires manual action)</p>
            </div>
            
            <div class="commands">
                <h3>📋 Available Commands:</h3>
                <strong>📊 Inventory Management:</strong><br>
                • <code>help</code> - Show all commands<br>
                • <code>inventory</code> - View current stock<br>
                • <code>item=quantity</code> - Set item quantity<br>
                • <code>add item=quantity</code> - Add to existing stock<br>
                • <code>sell item=quantity</code> - Remove from stock<br><br>
                
                <strong>👥 Group Management:</strong><br>
                • <code>members</code> - View all members<br>
                • <code>addmember &lt;number&gt;</code> - Add new member (admin only)<br>
                • <code>kick &lt;number&gt;</code> - Remove member (admin only)<br>
                • <code>reset</code> - Clear all inventory (admin only)<br><br>
                
                <strong>💡 Examples:</strong><br>
                • <code>apple=10, banana=5, orange=8</code><br>
                • <code>add apple=5</code><br>
                • <code>sell banana=3</code>
            </div>
            
            <p><strong>Webhook URL:</strong> {request.host_url}webhook</p>
        </div>
    </body>
    </html>
    """

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Webhook verification
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        expected_token = os.getenv('VERIFY_TOKEN')
        
        if mode == 'subscribe' and token == expected_token:
            return challenge
        else:
            return "Verification failed", 403
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            
            if data and 'entry' in data:
                for entry in data['entry']:
                    if 'changes' in entry:
                        for change in entry['changes']:
                            if 'value' in change and 'messages' in change['value']:
                                for message_data in change['value']['messages']:
                                    phone_number = message_data['from']
                                    message = message_data['text']['body'].lower().strip()
                                    
                                    print(f"📱 Message from {phone_number}: {message}")
                                    
                                    # Add/update member in database
                                    add_or_update_member(phone_number)
                                    
                                    # Process the message
                                    response = process_message(phone_number, message)
                                    
                                    # Send response
                                    if response:
                                        send_whatsapp_message(phone_number, response)
            
            return "OK"
            
        except Exception as e:
            print(f"❌ Error processing webhook: {e}")
            return "Error", 500

def process_message(phone_number, message):
    """Process incoming message and return response"""
    admin = is_admin(phone_number)
    
    if message == 'help':
        return """🤖 *WhatsApp Inventory Bot*

📊 *Inventory Commands:*
• help - Show this menu
• inventory - View current stock
• item=quantity - Set item quantity
• add item=quantity - Add to existing stock
• sell item=quantity - Remove from stock

👥 *Group Commands:*
• members - View all members

🔧 *Admin Commands:*
• addmember <number> - Add new member (admin only)
• kick <number> - Remove member (admin only)
• reset - Clear all inventory (admin only)

💡 *Examples:*
• apple=10, banana=5, orange=8
• add apple=5
• sell banana=3

🔒 *Data Protection:* All data is permanently stored in database!"""
    
    elif message == 'inventory':
        inventory = get_inventory()
        if not inventory:
            return "📦 Inventory is empty!"
        
        response = "📦 *Current Inventory:*\n"
        for item, quantity in inventory.items():
            response += f"• {item}: {quantity}\n"
        return response
    
    elif message == 'members':
        members = get_all_members()
        if not members:
            return "👥 No members found!"
        
        response = f"👥 *Group Members ({len(members)}):*\n"
        for phone, info in members.items():
            admin_badge = " 👑" if info.get('is_admin', False) else ""
            response += f"• {phone}{admin_badge} (Messages: {info.get('message_count', 0)})\n"
        return response
    
    elif message.startswith('addmember '):
        if not admin:
            return "❌ Only admins can add members!"
        
        try:
            parts = message.split(' ', 1)
            if len(parts) < 2:
                return "❌ Usage: addmember <phone_number>"
            
            new_phone = parts[1].strip()
            
            if not new_phone.isdigit() or len(new_phone) < 10:
                return "❌ Please provide a valid phone number"
            
            # Check if already exists
            members = get_all_members()
            if new_phone in members:
                return f"📱 {new_phone} is already a member!"
            
            # Add to database
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO members (phone_number, name, joined_date, is_admin, message_count, last_activity)
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', (new_phone, f"User {new_phone}", datetime.now(), is_admin(new_phone), 0, datetime.now()))
                conn.commit()
                conn.close()
                
                return f"✅ Added {new_phone} to the group!"
            else:
                return "❌ Database error"
                
        except Exception as e:
            return f"❌ Error adding member: {str(e)}"
    
    elif message.startswith('kick '):
        if not admin:
            return "❌ Only admins can kick members!"
        
        try:
            parts = message.split(' ', 1)
            if len(parts) < 2:
                return "❌ Usage: kick <phone_number>"
            
            target_phone = parts[1].strip()
            
            if target_phone in GROUP_ADMINS:
                return "❌ Cannot kick admin users!"
            
            members = get_all_members()
            if target_phone not in members:
                return f"❌ {target_phone} is not a member!"
            
            if remove_member(target_phone):
                return f"✅ Kicked {target_phone} from the group!"
            else:
                return "❌ Database error"
                
        except Exception as e:
            return f"❌ Error kicking member: {str(e)}"
    
    elif message == 'reset':
        if not admin:
            return "❌ Only admins can reset inventory!"
        
        if clear_inventory():
            return "✅ Inventory cleared!"
        else:
            return "❌ Database error"
    
    else:
        try:
            return handle_inventory_command(message)
        except Exception as e:
            return f"❌ Error: {str(e)}\n\nType 'help' for available commands."

def handle_inventory_command(message):
    """Handle inventory-related commands"""
    operation = "set"
    if message.startswith('add '):
        operation = "add"
        message = message[4:]
    elif message.startswith('sell '):
        operation = "sell"
        message = message[5:]
    
    items = [item.strip() for item in message.split(',')]
    results = []
    current_inventory = get_inventory()
    
    for item in items:
        if '=' not in item:
            results.append(f"❌ Invalid format: {item}")
            continue
        
        try:
            name, qty_str = item.split('=', 1)
            name = name.strip().lower()
            quantity = int(qty_str.strip())
            
            if quantity < 0:
                results.append(f"❌ {name}: Quantity cannot be negative")
                continue
            
            current_qty = current_inventory.get(name, 0)
            
            if operation == "set":
                new_qty = quantity
            elif operation == "add":
                new_qty = current_qty + quantity
            elif operation == "sell":
                new_qty = current_qty - quantity
                if new_qty < 0:
                    results.append(f"❌ {name}: Cannot sell {quantity} (only {current_qty} available)")
                    continue
            
            if update_inventory(name, new_qty):
                if new_qty == 0:
                    results.append(f"✅ {name}: Removed from inventory")
                else:
                    results.append(f"✅ {name}: {new_qty}")
            else:
                results.append(f"❌ {name}: Database error")
                
        except ValueError:
            results.append(f"❌ {item}: Invalid quantity")
        except Exception as e:
            results.append(f"❌ {item}: Error - {str(e)}")
    
    return "\n".join(results)

@app.route('/backup')
def backup():
    """Full database backup"""
    return jsonify({
        'members': get_all_members(),
        'inventory': get_inventory(),
        'backup_time': datetime.now().isoformat(),
        'storage_type': 'PostgreSQL Database'
    })

@app.route('/health')
def health():
    conn = get_db_connection()
    db_status = "connected" if conn else "disconnected"
    if conn:
        conn.close()
    
    return jsonify({
        'status': 'healthy',
        'database': db_status,
        'members': len(get_all_members()),
        'inventory_items': len(get_inventory()),
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
