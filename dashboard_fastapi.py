from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
import json
import os
import re
import time
import hashlib
import uuid
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

app = FastAPI()

# ==========================================
# 🔐 GOOGLE OAUTH CONFIGURATION
# ==========================================

# ✅ REPLACE WITH YOUR REAL GOOGLE CREDENTIALS
GOOGLE_CLIENT_ID = "425975360883-khqg707cmt1nthr2s9pcg9bmam0ejusq.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"

# ==========================================

# ==========================================
# 📧 EMAIL CONFIGURATION (For Bug Reports)
# ==========================================

# ✅ REPLACE WITH YOUR REAL EMAIL AND APP PASSWORD
YOUR_EMAIL = "omar.abdelsattar2020@gmail.com"          # ← Replace with your real email
APP_PASSWORD = "sqff rkjn brtw ofgo"           # ← Replace with your real App Password

# ==========================================

# ==========================================
# 🔐 USER DATABASE
# ==========================================

USERS = {}  # No demo users - real email only

SESSIONS = {}
SESSION_EXPIRY = {}

def get_user_data_file(email):
    safe_email = email.replace("@", "_at_").replace(".", "_dot_")
    return f"user_data_{safe_email}.json"

def load_products(email):
    try:
        with open(get_user_data_file(email), 'r') as f:
            return json.load(f)
    except:
        return []

def save_products(email, products):
    try:
        with open(get_user_data_file(email), 'w') as f:
            json.dump(products, f)
    except:
        pass

def clean_expired_sessions():
    now = datetime.now()
    expired = [sid for sid, expiry in SESSION_EXPIRY.items() if expiry < now]
    for sid in expired:
        if sid in SESSIONS:
            del SESSIONS[sid]
        del SESSION_EXPIRY[sid]

# ==========================================
# 📧 SEND BUG REPORT EMAIL
# ==========================================

def send_bug_report(email, bug_description, page_url):
    """Send bug report to admin email"""
    subject = f"🐛 Bug Report from {email}"
    
    body = f"""
🐛 BUG REPORT

📧 From: {email}
📄 Page: {page_url}
📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📝 Description:
{bug_description}

---
This report was sent from Price Scout.
"""
    
    try:
        msg = MIMEMultipart()
        msg['From'] = YOUR_EMAIL
        msg['To'] = YOUR_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(YOUR_EMAIL, APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"❌ Email failed: {e}")
        return False

# ==========================================
# 🏠 LOGIN PAGE
# ==========================================

LOGIN_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    
    <title>Price Scout - Track Any Product Price</title>
    <meta name="description" content="Track product prices from Amazon, Noon, and other stores. Get email alerts when prices drop.">
    <meta name="robots" content="index, follow">
    <meta property="og:title" content="Price Scout - Track Any Product Price">
    <meta property="og:description" content="Track product prices from Amazon, Noon, and other stores. Get alerts when prices drop.">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://price-tracker-x5nt.onrender.com">
    <link rel="canonical" href="https://price-tracker-x5nt.onrender.com">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🛒</text></svg>">
    
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": "Price Scout",
        "description": "Track product prices from Amazon, Noon, and other stores. Get alerts when prices drop.",
        "applicationCategory": "Shopping",
        "operatingSystem": "All",
        "browserRequirements": "Requires JavaScript",
        "url": "https://price-tracker-x5nt.onrender.com"
    }
    </script>
    
    <title>🔐 Login - Price Scout</title>
    <style>
        body { background: #0f0f1a; color: #fff; font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-box { background: #1a1a2e; padding: 40px; border-radius: 15px; border: 1px solid #2a2a4e; width: 380px; text-align: center; }
        h1 { color: #00d4ff; }
        .subtitle { color: #888; margin-bottom: 25px; }
        .google-btn { display: inline-block; background: #4285F4; color: white; padding: 12px 30px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 16px; margin-top: 10px; width: 100%; box-sizing: border-box; }
        .google-btn:hover { background: #357ae8; }
        .divider { display: flex; align-items: center; margin: 20px 0; color: #555; }
        .divider::before, .divider::after { content: ''; flex: 1; border-bottom: 1px solid #2a2a4e; }
        .divider span { padding: 0 15px; }
        input { width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px; border: 1px solid #2a2a4e; background: #0f0f1a; color: #fff; font-size: 16px; box-sizing: border-box; }
        input:focus { outline: none; border-color: #00d4ff; }
        button { width: 100%; padding: 12px; border-radius: 8px; border: none; background: #00d4ff; color: #000; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 10px; }
        button:hover { background: #00b8e6; }
        .error { color: #ff6b6b; margin: 10px 0; }
        .info { color: #888; font-size: 13px; margin-top: 15px; }
        .remember-me { display: flex; align-items: center; gap: 8px; margin: 10px 0; color: #888; font-size: 14px; }
        .remember-me input { width: auto; margin: 0; }
        .footer-text { color: #555; font-size: 12px; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🛒 Price Scout</h1>
        <p class="subtitle">Sign in to track your products</p>
        
        <a href="/auth/google" class="google-btn">🔑 Sign in with Google</a>
        
        <div class="divider"><span>or</span></div>
        
        <form method="POST" action="/login">
            <input type="email" name="email" placeholder="Your real email address" required>
            <input type="password" name="password" placeholder="Your password (min 4 characters)" required minlength="4">
            <div class="remember-me">
                <input type="checkbox" name="remember_me" id="remember_me" checked>
                <label for="remember_me">Remember me for 7 days</label>
            </div>
            <button type="submit">🔓 Create Account / Login</button>
        </form>
        <div class="info">💡 New users: Use your real email and create a password</div>
        <div class="footer-text">🔒 Your data is private and secure</div>
        {error}
    </div>
</body>
</html>
"""

# ==========================================
# 📊 DASHBOARD (WITH REPORT BUG BUTTON)
# ==========================================

def get_dashboard_html(email, products, message=None, message_type=None):
    total = len(products)
    dropped = sum(1 for p in products if p.get('status') == 'dropped')
    errors = sum(1 for p in products if p.get('status') == 'error')
    waiting = total - dropped - errors
    
    products_html = ""
if products:
    for i, p in enumerate(products):
        status_class = "dropped" if p.get('status') == 'dropped' else "error" if p.get('status') == 'error' else ""
        price_class = "price-green" if p.get('status') == 'dropped' else "price-red" if p.get('status') == 'error' else "price-yellow"
        
        if p.get('status') == 'dropped':
            status_text = "✅ Price Dropped!"
            badge_class = "status-dropped"
        elif p.get('status') == 'error':
            status_text = "❌ Error"
            badge_class = "status-error"
        else:
            status_text = "⏳ Waiting"
            badge_class = "status-waiting"
        
        # ✅ THIS IS THE FIXED LINE
        price_display = f"SAR {p.get('current_price', 'N/A')}"
        
        products_html += f"""
        <div class="product-card {status_class}">
            <div class="product-name">
                <div>{p.get('name', 'Unknown')}</div>
                <div class="product-url"><a href="{p.get('url', '#')}" target="_blank" style="color: #00d4ff;">🔗 View Product</a></div>
            </div>
            <div class="product-price {price_class}">
                {price_display}
                <div style="font-size: 14px; color: #888;">Target: SAR {p.get('target', 0)}</div>
            </div>
            <div class="product-status">
                <span class="status-badge {badge_class}">{status_text}</span>
            </div>
            <div class="product-actions">
                <form method="POST" action="/remove_product/{i}" style="display:inline;">
                    <button type="submit">✕ Remove</button>
                </form>
            </div>
        </div>
        """
else:
    products_html = """
    <div style="text-align: center; padding: 50px; color: #555;">
        <h3>📭 No products being tracked</h3>
        <p>Add your first product using the form above!</p>
    </div>
    """
    
    message_html = ""
    if message:
        msg_class = "success" if message_type == "success" else "error-msg"
        message_html = f'<div class="message {msg_class}">{message}</div>'
    
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    
    <title>Price Scout - Track Any Product Price</title>
    <meta name="description" content="Track product prices from Amazon, Noon, and other stores. Get email alerts when prices drop.">
    <meta name="robots" content="index, follow">
    <meta property="og:title" content="Price Scout - Track Any Product Price">
    <meta property="og:description" content="Track product prices from Amazon, Noon, and other stores. Get alerts when prices drop.">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://price-tracker-x5nt.onrender.com">
    <link rel="canonical" href="https://price-tracker-x5nt.onrender.com">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🛒</text></svg>">
    
    <title>🛒 Price Scout</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f0f1a; color: #fff; padding: 20px; min-height: 100vh; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 30px; border-radius: 15px; margin-bottom: 30px; border: 1px solid #2a2a4e; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }}
        .header h1 {{ color: #00d4ff; font-size: 28px; }}
        .header p {{ color: #888; }}
        .header-actions {{ display: flex; align-items: center; gap: 15px; }}
        .report-btn {{ background: #ff6b6b22; color: #ff6b6b; border: 1px solid #ff6b6b; padding: 6px 15px; border-radius: 20px; text-decoration: none; font-size: 13px; font-weight: 600; transition: all 0.3s; }}
        .report-btn:hover {{ background: #ff6b6b44; }}
        .logout {{ color: #ff6b6b; text-decoration: none; margin-left: 15px; }}
        .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }}
        .stat-card {{ background: #1a1a2e; padding: 20px; border-radius: 12px; text-align: center; border: 1px solid #2a2a4e; }}
        .stat-number {{ font-size: 28px; font-weight: bold; color: #00d4ff; }}
        .stat-label {{ color: #888; font-size: 14px; margin-top: 5px; }}
        .add-section {{ background: #1a1a2e; padding: 25px; border-radius: 12px; margin-bottom: 30px; border: 1px solid #2a2a4e; }}
        .add-section h2 {{ color: #00d4ff; margin-bottom: 15px; }}
        .add-form {{ display: flex; flex-wrap: wrap; gap: 10px; }}
        .add-form input {{ flex: 1; min-width: 200px; padding: 12px; border-radius: 8px; border: 1px solid #2a2a4e; background: #0f0f1a; color: #fff; font-size: 14px; }}
        .add-form button {{ padding: 12px 30px; border-radius: 8px; border: none; background: #00d4ff; color: #000; font-weight: bold; cursor: pointer; }}
        .add-form button:hover {{ background: #00b8e6; }}
        .product-card {{ background: #1a1a2e; padding: 15px 20px; border-radius: 12px; margin-bottom: 10px; border-left: 4px solid #2a2a4e; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }}
        .product-card.dropped {{ border-left-color: #00ff88; background: #00ff8810; }}
        .product-card.error {{ border-left-color: #ff6b6b; background: #ff6b6b10; }}
        .product-name {{ font-weight: 600; flex: 1; min-width: 150px; }}
        .product-url {{ color: #555; font-size: 12px; }}
        .product-price {{ font-size: 22px; font-weight: bold; min-width: 100px; }}
        .price-green {{ color: #00ff88; }}
        .price-red {{ color: #ff6b6b; }}
        .price-yellow {{ color: #ffaa00; }}
        .product-status {{ min-width: 90px; text-align: center; }}
        .status-badge {{ padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
        .status-dropped {{ background: #00ff8822; color: #00ff88; border: 1px solid #00ff88; }}
        .status-waiting {{ background: #ffaa0022; color: #ffaa00; border: 1px solid #ffaa00; }}
        .status-error {{ background: #ff6b6b22; color: #ff6b6b; border: 1px solid #ff6b6b; }}
        .product-actions button {{ background: #ff6b6b; color: #fff; border: none; padding: 5px 12px; border-radius: 5px; cursor: pointer; }}
        .product-actions button:hover {{ background: #e55a5a; }}
        .footer {{ text-align: center; color: #555; margin-top: 30px; padding: 20px; border-top: 1px solid #1a1a2e; }}
        .message {{ padding: 10px; border-radius: 8px; margin-bottom: 15px; }}
        .success {{ background: #00ff8822; color: #00ff88; border: 1px solid #00ff88; }}
        .error-msg {{ background: #ff6b6b22; color: #ff6b6b; border: 1px solid #ff6b6b; }}
        
        /* Bug Report Modal */
        .modal {{
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }}
        .modal.show {{ display: flex; }}
        .modal-content {{
            background: #1a1a2e;
            padding: 30px;
            border-radius: 15px;
            width: 500px;
            max-width: 90%;
            border: 1px solid #2a2a4e;
        }}
        .modal-content h2 {{ color: #00d4ff; margin-bottom: 15px; }}
        .modal-content textarea {{
            width: 100%;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #2a2a4e;
            background: #0f0f1a;
            color: #fff;
            font-size: 14px;
            min-height: 120px;
            resize: vertical;
            margin: 10px 0;
        }}
        .modal-content textarea:focus {{ outline: none; border-color: #00d4ff; }}
        .modal-actions {{ display: flex; gap: 10px; margin-top: 15px; }}
        .modal-actions button {{ padding: 10px 25px; border-radius: 8px; border: none; cursor: pointer; font-weight: bold; }}
        .btn-send {{ background: #00d4ff; color: #000; }}
        .btn-send:hover {{ background: #00b8e6; }}
        .btn-cancel {{ background: #2a2a4e; color: #fff; }}
        .btn-cancel:hover {{ background: #3a3a5e; }}
        @media (max-width: 600px) {{
            .stats {{ grid-template-columns: repeat(2, 1fr); }}
            .product-card {{ flex-direction: column; align-items: stretch; text-align: center; }}
            .header {{ flex-direction: column; text-align: center; gap: 10px; }}
            .modal-content {{ width: 95%; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>🛒 Price Scout</h1>
                <p>Track any product from any website</p>
            </div>
            <div class="header-actions">
                <span style="color: #00d4ff;">👤 {email}</span>
                <a href="#" class="report-btn" onclick="openReportModal()">🐛 Report Bug</a>
                <a href="/logout" class="logout">🚪 Logout</a>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card"><div class="stat-number">{total}</div><div class="stat-label">📦 Products</div></div>
            <div class="stat-card"><div class="stat-number" style="color: #00ff88;">{dropped}</div><div class="stat-label">🔔 Price Drops</div></div>
            <div class="stat-card"><div class="stat-number" style="color: #ffaa00;">{waiting}</div><div class="stat-label">⏳ Waiting</div></div>
            <div class="stat-card"><div class="stat-number" style="color: #ff6b6b;">{errors}</div><div class="stat-label">❌ Errors</div></div>
        </div>
        
        <div class="add-section">
            <h2>➕ Add New Product</h2>
            <form class="add-form" method="POST" action="/add_product">
                <input type="url" name="url" placeholder="Paste product URL (Amazon, Noon, etc.)" required>
                <input type="number" name="target" placeholder="Target price (SAR)" required step="0.01" min="0.01">
                <button type="submit">🔍 Add & Track</button>
            </form>
            <div style="color: #888; font-size: 12px; margin-top: 10px;">💡 Supports: Amazon, Noon, Jarir, and most online stores</div>
        </div>
        
        {message_html}
        
        <h2 style="color: #888; margin-bottom: 15px;">📦 Your Products</h2>
        
        {products_html}
        
        <div class="footer">🔄 Refreshes every 5 minutes &nbsp;|&nbsp; Price Scout v2.0</div>
    </div>
    
    <!-- ===== BUG REPORT MODAL ===== -->
    <div id="bugModal" class="modal">
        <div class="modal-content">
            <h2>🐛 Report a Bug</h2>
            <p style="color: #888; font-size: 14px;">Describe the issue you're experiencing. We'll look into it!</p>
            <form id="bugForm" method="POST" action="/report_bug">
                <input type="hidden" name="page_url" id="page_url">
                <textarea name="bug_description" id="bug_description" placeholder="What went wrong? Please be as detailed as possible..." required></textarea>
                <div class="modal-actions">
                    <button type="button" class="btn-cancel" onclick="closeReportModal()">Cancel</button>
                    <button type="submit" class="btn-send">📧 Send Report</button>
                </div>
            </form>
        </div>
    </div>
    
    <script>
        function openReportModal() {{
            document.getElementById('bugModal').classList.add('show');
            document.getElementById('page_url').value = window.location.href;
        }}
        function closeReportModal() {{
            document.getElementById('bugModal').classList.remove('show');
        }}
        document.getElementById('bugModal').addEventListener('click', function(e) {{
            if (e.target === this) closeReportModal();
        }});
    </script>
</body>
</html>
    """

# ==========================================
# 🌐 ROUTES
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    clean_expired_sessions()
    session_id = request.cookies.get("session_id")
    if session_id and session_id in SESSIONS:
        return RedirectResponse(url="/dashboard", status_code=302)
    return LOGIN_PAGE

@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    remember_me: bool = Form(False)
):
    if len(password) < 4:
        error_msg = '<div class="error">❌ Password must be at least 4 characters</div>'
        return LOGIN_PAGE.replace("{error}", error_msg)
    
    if email in USERS:
        hashed = hashlib.sha256(password.encode()).hexdigest()
        if USERS[email] != hashed:
            error_msg = '<div class="error">❌ Invalid email or password</div>'
            return LOGIN_PAGE.replace("{error}", error_msg)
    else:
        USERS[email] = hashlib.sha256(password.encode()).hexdigest()
    
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = email
    
    if remember_me:
        expiry = datetime.now() + timedelta(days=7)
        max_age = 7 * 24 * 60 * 60
    else:
        expiry = datetime.now() + timedelta(hours=24)
        max_age = 24 * 60 * 60
    
    SESSION_EXPIRY[session_id] = expiry
    
    redirect_response = RedirectResponse(url="/dashboard", status_code=302)
    redirect_response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=max_age,
        httponly=True,
        samesite="lax"
    )
    return redirect_response

@app.get("/auth/google")
async def google_login():
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri=https://price-tracker-x5nt.onrender.com/auth/google/callback"
        f"&response_type=code"
        f"&scope=email%20profile"
    )
    return RedirectResponse(auth_url)

@app.get("/auth/google/callback")
async def google_callback(request: Request, code: str = None):
    if not code:
        return RedirectResponse(url="/?error=google_failed")
    
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': 'https://price-tracker-x5nt.onrender.com/auth/google/callback',
        'code': code,
        'grant_type': 'authorization_code'
    }
    
    try:
        response = requests.post(token_url, data=data)
        token_data = response.json()
        
        if 'access_token' not in token_data:
            return RedirectResponse(url="/?error=token_failed")
        
        userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        headers = {'Authorization': f"Bearer {token_data['access_token']}"}
        user_response = requests.get(userinfo_url, headers=headers)
        user_info = user_response.json()
        
        email = user_info.get('email')
        if not email:
            return RedirectResponse(url="/?error=no_email")
        
        if email not in USERS:
            USERS[email] = hashlib.sha256("google_oauth".encode()).hexdigest()
        
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = email
        SESSION_EXPIRY[session_id] = datetime.now() + timedelta(days=7)
        
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            key="session_id",
            value=session_id,
            max_age=7 * 24 * 60 * 60,
            httponly=True,
            samesite="lax"
        )
        return response
        
    except Exception as e:
        print(f"❌ Google auth error: {e}")
        return RedirectResponse(url="/?error=google_failed")

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session_id")
    
    session_id = request.cookies.get("session_id")
    if session_id:
        if session_id in SESSIONS:
            del SESSIONS[session_id]
        if session_id in SESSION_EXPIRY:
            del SESSION_EXPIRY[session_id]
    
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    clean_expired_sessions()
    session_id = request.cookies.get("session_id")
    
    if not session_id or session_id not in SESSIONS:
        return RedirectResponse(url="/", status_code=302)
    
    email = SESSIONS[session_id]
    products = load_products(email)
    
    message = request.query_params.get("message")
    message_type = "success" if message and "✅" in message else "error-msg"
    
    return get_dashboard_html(email, products, message, message_type)

def get_product_info(url):
    """Simple version without Selenium - works on Render"""
    try:
        import urllib.parse
        domain = urllib.parse.urlparse(url).netloc
        name = f"Product from {domain}"
        return name, None
    except:
        return "Unknown Product", None

@app.post("/add_product")
async def add_product(request: Request, url: str = Form(...), target: str = Form(...)):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in SESSIONS:
        return RedirectResponse(url="/", status_code=302)
    
    email = SESSIONS[session_id]
    
    try:
        target_price = float(target)
    except:
        return RedirectResponse(url="/dashboard?message=❌ Invalid target price", status_code=302)
    
    if not url.startswith('http'):
        return RedirectResponse(url="/dashboard?message=❌ Invalid URL", status_code=302)
    
    name, price = get_product_info(url)
    
    if not name or name == "Unknown Product":
        name = f"Product {len(load_products(email)) + 1}"
    
    products = load_products(email)
    products.append({
        "name": name,
        "url": url,
        "target": target_price,
        "current_price": price or 0,
        "status": "waiting"
    })
    save_products(email, products)
    
    return RedirectResponse(url=f"/dashboard?message=✅ {name[:40]} added!", status_code=302)

@app.post("/remove_product/{index}")
async def remove_product(request: Request, index: int):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in SESSIONS:
        return RedirectResponse(url="/", status_code=302)
    
    email = SESSIONS[session_id]
    products = load_products(email)
    
    if 0 <= index < len(products):
        products.pop(index)
        save_products(email, products)
    
    return RedirectResponse(url="/dashboard", status_code=302)

@app.post("/report_bug")
async def report_bug(
    request: Request,
    bug_description: str = Form(...),
    page_url: str = Form(...)
):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in SESSIONS:
        return RedirectResponse(url="/", status_code=302)
    
    email = SESSIONS[session_id]
    
    success = send_bug_report(email, bug_description, page_url)
    
    if success:
        return RedirectResponse(url="/dashboard?message=✅ Bug report sent! Thank you!", status_code=302)
    else:
        return RedirectResponse(url="/dashboard?message=❌ Failed to send report. Please try again.", status_code=302)

@app.get("/robots.txt")
async def robots():
    content = """User-agent: *
Allow: /
Disallow: /logout
Disallow: /remove_product/*
Disallow: /report_bug

Sitemap: https://price-tracker-x5nt.onrender.com/sitemap.xml
"""
    return Response(content=content, media_type="text/plain")

@app.get("/sitemap.xml")
async def sitemap():
    base_url = "https://price-tracker-x5nt.onrender.com"
    pages = [
        {"loc": f"{base_url}/", "priority": "1.0"},
        {"loc": f"{base_url}/dashboard", "priority": "0.9"},
    ]
    
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
'''
    for page in pages:
        xml += f'''<url>
    <loc>{page['loc']}</loc>
    <priority>{page['priority']}</priority>
</url>\n'''
    
    xml += '</urlset>'
    return Response(content=xml, media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("🛒 PRICE SCOUT — Dashboard")
    print("="*60)
    print("📧 Users sign up with real email")
    print("🐛 Bug reports sent to: " + YOUR_EMAIL)
    print("📊 URL: https://price-tracker-x5nt.onrender.com")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=10000)
