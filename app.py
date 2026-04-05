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

def send_dual_email(customer_email, items_text, total_price):
    try:
        # --- 1. ADMIN EMAIL (Keep as Plain Text) ---
        admin_msg = EmailMessage()
        admin_msg['Subject'] = "ADMIN: New Sale Alert"
        admin_msg['To'] = ADMIN_RECEIVER
        admin_msg['From'] = SENDER_EMAIL
        admin_msg.set_content(f"New Order Details:\nUser: {customer_email}\nItems: {items_text}\nTotal: ${total_price}")

        # --- 2. CUSTOMER EMAIL (HTML with Image) ---
        cust_msg = EmailMessage()
        cust_msg['Subject'] = "Order Confirmed - Webazon"
        cust_msg['To'] = customer_email
        cust_msg['From'] = SENDER_EMAIL

        # Plain text fallback (for old email clients)
        cust_msg.set_content(f"Hi! Your order is confirmed. Total: ${total_price}")

        # HTML Version with the Image Tag
        image_url = "https://tse4.mm.bing.net/th/id/OIP.5odo0uXi0cDJ3MatX6ID4wHaHa?pid=Api&P=0&h=220"
        
        html_content = f"""
        <html>
            <body>
                <h2 style="color: #f08804;">Order Confirmed!</h2>
                <p>Hi there, thank you for shopping with <strong>Webazon</strong>.</p>
                <p><strong>Items:</strong> {items_text}</p>
                <p><strong>Total:</strong> ${total_price}</p>
                <br>
                <img src="{image_url}" alt="Webazon Logo" width="50">
                <br>
                <p>Visit us again soon!</p>
            </body>
        </html>
        """
        cust_msg.add_alternative(html_content, subtype='html')

        # --- SENDING ---
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASS)
            smtp.send_message(admin_msg)
            smtp.send_message(cust_msg)
            
    except Exception as e:
        print(f"Mail Error: {e}")

# --- AUTH ROUTES ---
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if mongo.db.users.find_one({"email": data['email']}):
        return jsonify({"msg": "User already exists"}), 400
    
    hashed_pw = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    mongo.db.users.insert_one({
        "email": data['email'], 
        "password": hashed_pw, 
        "role": data.get('role', 'customer'),
        "cart": []
    })
    return jsonify({"msg": "Registration Successful! Log in now."}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = mongo.db.users.find_one({"email": data['email']})
    if user and bcrypt.check_password_hash(user['password'], data['password']):
        return jsonify({"role": user['role'], "email": user['email']}), 200
    return jsonify({"msg": "Invalid Login"}), 401

# --- PRODUCT & ORDER ROUTES ---
@app.route('/api/products', methods=['GET', 'POST'])
def handle_products():
    if request.method == 'POST':
        data = request.json # { name, price, image_url, role }
        if data.get('role') == 'admin':
            mongo.db.products.insert_one({
                "name": data['name'], 
                "price": int(data['price']),
                "image_url": data.get('image_url', 'https://via.placeholder.com/150')
            })
            return jsonify({"msg": "Product Added"}), 201
        return jsonify({"msg": "Unauthorized"}), 403
    
    # Include image_url in the results
    products = list(mongo.db.products.find({}, {'_id': 0}))
    return jsonify(products)

@app.route('/api/checkout', methods=['POST'])
def checkout():
    data = request.json # {email, items, total}
    mongo.db.orders.insert_one(data)
    send_dual_email(data['email'], data['items'], data['total'])
    return jsonify({"msg": "Order Successful!"})

if __name__ == "__main__":
    app.run(debug=True)