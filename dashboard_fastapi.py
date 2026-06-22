from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
import json
import os
import re
import time
import hashlib
import uuid
import requests
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

app = FastAPI()

# ==========================================
# 🔐 GOOGLE OAUTH CONFIGURATION
# ==========================================

# ✅ REPLACE THESE WITH YOUR REAL CREDENTIALS
GOOGLE_CLIENT_ID = " 425975360883-khqg707cmt1nthr2s9pcg9bmam0ejusq.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"

# ==========================================

SESSIONS = {}

def get_user_data_file(email):
    """Each user gets their own data file"""
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

# ==========================================
# 🕷️ SCRAPER
# ==========================================

def get_product_info(url):
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get(url)
        time.sleep(3)
        
        name = "Unknown Product"
        selectors = [
            "#productTitle", ".product-title", "h1",
            ".productDetailsTitle", ".product-title__text",
            "[data-testid='product-title']"
        ]
        for selector in selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                name = element.text.strip()
                if name and len(name) > 3:
                    break
            except:
                pass
        
        price = None
        page_text = driver.page_source
        
        patterns = [
            r'(\d+\.?\d*)\s*SAR',
            r'SAR\s*(\d+\.?\d*)',
            r'ريال\s*(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*ريال',
            r'\$(\d+\.?\d*)',
            r'(\d+\.?\d*)\s*دولار',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, page_text)
            if matches:
                for match in matches:
                    try:
                        val = float(match)
                        if 1 < val < 100000:
                            price = val
                            break
                    except:
                        pass
                if price:
                    break
        
        if price is None:
            try:
                price_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='price'], [class*='Price']")
                for elem in price_elements:
                    text = elem.text.strip()
                    numbers = re.findall(r'(\d+\.?\d*)', text)
                    if numbers:
                        for num in numbers:
                            try:
                                val = float(num)
                                if 1 < val < 100000:
                                    price = val
                                    break
                            except:
                                pass
                    if price:
                        break
            except:
                pass
        
        driver.quit()
        return name, price
        
    except Exception as e:
        print(f"❌ Scraper error: {e}")
        return "Unknown Product", None

# ==========================================
# 🏠 LOGIN PAGE
# ==========================================

LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🛒 Price Scout</h1>
        <p class="subtitle">Sign in to track your products</p>
        
        <a href="/auth/google" class="google-btn">🔑 Sign in with Google</a>
        
        <div class="divider"><span>or</span></div>
        
        <form method="POST" action="/login">
            <input type="email" name="email" placeholder="Email address" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">🔓 Login / Sign Up</button>
        </form>
        <div class="info">💡 New users are automatically registered</div>
    </div>
</body>
</html>
"""

# ==========================================
# 📊 DASHBOARD
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
            
            price_display = f"${p.get('current_price', 'N/A')}" if p.get('current_price') else "N/A"
            
            products_html += f"""
            <div class="product-card {status_class}">
                <div class="product-name">
                    <div>{p.get('name', 'Unknown')}</div>
                    <div class="product-url"><a href="{p.get('url', '#')}" target="_blank" style="color: #00d4ff;">🔗 View Product</a></div>
                </div>
                <div class="product-price {price_class}">
                    {price_display}
                    <div style="font-size: 14px; color: #888;">Target: ${p.get('target', 0)}</div>
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
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🛒 Price Scout</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f0f1a; color: #fff; padding: 20px; min-height: 100vh; }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 30px; border-radius: 15px; margin-bottom: 30px; border: 1px solid #2a2a4e; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; }}
        .header h1 {{ color: #00d4ff; font-size: 28px; }}
        .header p {{ color: #888; }}
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
        @media (max-width: 600px) {{
            .stats {{ grid-template-columns: repeat(2, 1fr); }}
            .product-card {{ flex-direction: column; align-items: stretch; text-align: center; }}
            .header {{ flex-direction: column; text-align: center; gap: 10px; }}
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
            <div>
                <span style="color: #00d4ff;">👤 {email}</span>
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
                <input type="number" name="target" placeholder="Target price (SAR or $)" required step="0.01" min="0.01">
                <button type="submit">🔍 Add & Track</button>
            </form>
            <div style="color: #888; font-size: 12px; margin-top: 10px;">💡 Supports: Amazon, Noon, Jarir, and most online stores</div>
        </div>
        
        {message_html}
        
        <h2 style="color: #888; margin-bottom: 15px;">📦 Your Products</h2>
        
        {products_html}
        
        <div class="footer">🔄 Refreshes every 5 minutes &nbsp;|&nbsp; Price Scout v2.0</div>
    </div>
    
    <script>
        setInterval(function() {{ location.reload(); }}, 300000);
    </script>
</body>
</html>
    """

# ==========================================
# 🌐 ROUTES
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id and session_id in SESSIONS:
        return RedirectResponse(url="/dashboard", status_code=302)
    return LOGIN_PAGE

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, response: Response, email: str = Form(...), password: str = Form(...)):
    # Simple login for demo
    if email == "demo@email.com" and password == "demo123":
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = email
        redirect_response = RedirectResponse(url="/dashboard", status_code=302)
        redirect_response.set_cookie(key="session_id", value=session_id, max_age=7*24*60*60)
        return redirect_response
    
    # For new users: auto-register
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = email
    redirect_response = RedirectResponse(url="/dashboard", status_code=302)
    redirect_response.set_cookie(key="session_id", value=session_id, max_age=7*24*60*60)
    return redirect_response

@app.get("/auth/google")
async def google_login():
    """Redirect to Google OAuth"""
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri=http://127.0.0.1:5000/auth/google/callback"
        f"&response_type=code"
        f"&scope=email%20profile"
    )
    return RedirectResponse(auth_url)

@app.get("/auth/google/callback")
async def google_callback(request: Request, code: str = None):
    """Handle Google OAuth callback"""
    if not code:
        return RedirectResponse(url="/?error=google_failed")
    
    # Exchange code for token
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': 'http://127.0.0.1:5000/auth/google/callback',
        'code': code,
        'grant_type': 'authorization_code'
    }
    
    try:
        response = requests.post(token_url, data=data)
        token_data = response.json()
        
        if 'access_token' not in token_data:
            return RedirectResponse(url="/?error=token_failed")
        
        # Get user info
        userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        headers = {'Authorization': f"Bearer {token_data['access_token']}"}
        user_response = requests.get(userinfo_url, headers=headers)
        user_info = user_response.json()
        
        email = user_info.get('email')
        if not email:
            return RedirectResponse(url="/?error=no_email")
        
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = email
        
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(key="session_id", value=session_id, max_age=7*24*60*60)
        return response
        
    except Exception as e:
        print(f"❌ Google auth error: {e}")
        return RedirectResponse(url="/?error=google_failed")

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session_id")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in SESSIONS:
        return RedirectResponse(url="/", status_code=302)
    
    email = SESSIONS[session_id]
    products = load_products(email)
    
    message = request.query_params.get("message")
    message_type = "success" if message and "✅" in message else "error-msg"
    
    return get_dashboard_html(email, products, message, message_type)

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

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("🛒 PRICE SCOUT — Dashboard")
    print("="*60)
    print("📧 Login with Google OR Email/Password")
    print("🔑 Demo: demo@email.com / demo123")
    print("✅ Each user has their own products")
    print("="*60)
    print("📊 URL: http://127.0.0.1:5000")
    print("="*60)
    
    uvicorn.run(app, host="127.0.0.1", port=5000)