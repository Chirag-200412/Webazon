from flask import Flask, request, jsonify
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import smtplib
from email.message import EmailMessage

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

# MongoDB Setup
app.config["MONGO_URI"] = "mongodb://localhost:27017/amazon_clone"
mongo = PyMongo(app)

# --- EMAIL CONFIGURATION ---
SENDER_EMAIL = "chiragagrawal1500@gmail.com" 
SENDER_PASS = "tznmbalahthurtmx" # Your 16-digit App Password
ADMIN_RECEIVER = "chiragagrawal1500@gmail.com"

def send_dual_email(customer_email, items_text, total_price, pay_method, tid):
    try:
        # 1. ADMIN NOTIFICATION (Verification Receipt)
        admin_msg = EmailMessage()
        admin_msg['Subject'] = f"💳 VERIFY PAYMENT: {pay_method} - ${total_price}"
        admin_msg['To'] = ADMIN_RECEIVER
        admin_msg['From'] = SENDER_EMAIL
        
        admin_content = f"""
        WEB-AZON: NEW ORDER PENDING
        ---------------------------
        Customer: {customer_email}
        Items: {items_text}
        Total: ${total_price}
        
        PAYMENT PROOF:
        Method: {pay_method}
        Transaction ID: {tid}
        
        Note: Verify ID {tid} in your Paytm App before shipping.
        """
        admin_msg.set_content(admin_content)

        # 2. CUSTOMER RECEIPT (HTML with Logo)
        cust_msg = EmailMessage()
        cust_msg['Subject'] = "Order Received - Webazon"
        cust_msg['To'] = customer_email
        cust_msg['From'] = SENDER_EMAIL
        
        logo_url = "https://tse4.mm.bing.net/th/id/OIP.5odo0uXi0cDJ3MatX6ID4wHaHa?pid=Api&P=0&h=220"
        html_content = f"""
        <html>
            <body style="font-family: Arial; border: 1px solid #eee; padding: 20px;">
                <h2 style="color: #f08804;">Your Order is Placed!</h2>
                <p>We are verifying your <strong>{pay_method}</strong> payment (ID: {tid}).</p>
                <div style="background:#f9f9f9; padding:10px; border-radius:5px;">
                    <p><strong>Items:</strong> {items_text}</p>
                    <p><strong>Total Amount:</strong> ${total_price}</p>
                </div>
                <br>
                <img src="{logo_url}" alt="Webazon Logo" width="100">
                <p>Thank you for shopping with Webazon!</p>
            </body>
        </html>
        """
        cust_msg.add_alternative(html_content, subtype='html')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASS)
            smtp.send_message(admin_msg)
            smtp.send_message(cust_msg)
    except Exception as e:
        print(f"Mail Error: {e}")

# --- ROUTES ---

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if mongo.db.users.find_one({"email": data['email']}):
        return jsonify({"msg": "Email already registered"}), 400
    
    hashed_pw = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    mongo.db.users.insert_one({
        "email": data['email'], 
        "password": hashed_pw, 
        "role": data.get('role', 'customer'),
        "cart": []
    })
    return jsonify({"msg": "Registration Successful!"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = mongo.db.users.find_one({"email": data['email']})
    if user and bcrypt.check_password_hash(user['password'], data['password']):
        return jsonify({
            "role": user['role'], "email": user['email'], "cart": user.get('cart', [])
        }), 200
    return jsonify({"msg": "Invalid Credentials"}), 401

@app.route('/api/sync-cart', methods=['POST'])
def sync_cart():
    data = request.json
    mongo.db.users.update_one({"email": data['email']}, {"$set": {"cart": data['cart']}})
    return jsonify({"msg": "Synced"}), 200

@app.route('/api/products', methods=['GET', 'POST'])
def handle_products():
    if request.method == 'POST':
        data = request.json
        if data.get('role') == 'admin':
            mongo.db.products.insert_one({
                "name": data['name'], "price": int(data['price']), "image_url": data.get('image_url', '')
            })
            return jsonify({"msg": "Product Added"}), 201
        return jsonify({"msg": "Unauthorized"}), 403
    return jsonify(list(mongo.db.products.find({}, {'_id': 0})))

@app.route('/api/delete-product', methods=['POST'])
def delete_product():
    data = request.json
    if data.get('role') == 'admin':
        mongo.db.products.delete_one({"name": data['name']})
        return jsonify({"msg": "Deleted"}), 200
    return jsonify({"msg": "Forbidden"}), 403

@app.route('/api/checkout', methods=['POST'])
def checkout():
    try:
        data = request.json
        # 1. Save order to MongoDB
        mongo.db.orders.insert_one(data)
        
        # 2. Extract info for Email
        email = data.get('email')
        items = data.get('items')
        total = data.get('total')
        method = data.get('payment_method')
        tid = data.get('transaction_id', 'N/A')

        # 3. Send Dual Emails
        send_dual_email(email, items, total, method, tid)
        
        # 4. Clear Cart in DB
        mongo.db.users.update_one({"email": email}, {"$set": {"cart": []}})
        
        return jsonify({"msg": "Order placed successfully!"}), 200
    except Exception as e:
        print(f"Checkout Error: {e}")
        return jsonify({"msg": "Server error during checkout"}), 500

if __name__ == "__main__":
    app.run(debug=True)