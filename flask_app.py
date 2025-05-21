from flask import Flask, request, Response, session, redirect, url_for
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with a secure random key

PROXY_PREFIX = "https://proxy-made-with-pain.onrender.com/proxy?url="

# Simple in-memory user store (username -> password)
users = {}

# Store user sessions here (in-memory)
user_sessions = {}

def get_user_session():
    user_id = session.get('user_id')
    if not user_id:
        user_id = str(uuid.uuid4())
        session['user_id'] = user_id
    if user_id not in user_sessions:
        user_sessions[user_id] = requests.Session()
    return user_sessions[user_id]

def rewrite_html(content, base_url):
    soup = BeautifulSoup(content, 'html.parser')
    tags_attrs = {
        'a': 'href',
        'img': 'src',
        'script': 'src',
        'link': 'href',
        'iframe': 'src',
        'source': 'src',
        'form': 'action'
    }
    for tag, attr in tags_attrs.items():
        for element in soup.find_all(tag):
            if not element.has_attr(attr):
                continue
            original_url = element[attr]
            absolute_url = urljoin(base_url, original_url)
            if tag in ['img', 'script', 'source', 'link', 'iframe']:
                element[attr] = absolute_url
            elif tag in ['a', 'form']:
                proxied_url = PROXY_PREFIX + quote(absolute_url)
                element[attr] = proxied_url
                if tag == 'form':
                    method = element.get('method', '').lower()
                    if method not in ['get', 'post']:
                        element['method'] = 'post'
    return str(soup)

def login_required(func):
    from functools import wraps
    @wraps(func)
    def wrapped(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login_page'))
        return func(*args, **kwargs)
    return wrapped

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return "Username and password required", 400
        if username in users:
            return "Username already exists", 400
        users[username] = password
        return "Signup successful! You can now log in."
    # Simple signup form
    return '''
    <form method="post">
      Username: <input name="username" /><br/>
      Password: <input type="password" name="password" /><br/>
      <button type="submit">Sign Up</button>
    </form>
    '''

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return "Username and password required", 400
        if users.get(username) != password:
            return "Invalid credentials", 401
        session['logged_in'] = True
        session['username'] = username
        return redirect(url_for('proxy'))
    # Simple login form
    return '''
    <form method="post">
      Username: <input name="username" /><br/>
      Password: <input type="password" name="password" /><br/>
      <button type="submit">Log In</button>
    </form>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return "Logged out!"

@app.route('/proxy', methods=['GET', 'POST'])
@login_required
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return "Missing url parameter", 400

    try:
        user_sess = get_user_session()
        method = request.method

        headers = {k: v for k, v in request.headers if k.lower() not in ['host', 'cookie']}

        if method == 'POST':
            resp = user_sess.post(target_url, headers=headers, data=request.form, stream=True)
        else:
            resp = user_sess.get(target_url, headers=headers, params=request.args, stream=True)

        content_type = resp.headers.get('Content-Type', '')
        if 'text/html' in content_type:
            content = rewrite_html(resp.text, target_url)
            content = content.encode(resp.encoding or 'utf-8')
        else:
            content = resp.content

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]

        response_headers.append(('Access-Control-Allow-Origin', '*'))
        response_headers.append(('X-Frame-Options', 'ALLOWALL'))
        response_headers.append(('Content-Security-Policy', 'frame-ancestors *'))
        response_headers.append(('Cross-Origin-Embedder-Policy', 'unsafe-none'))
        response_headers.append(('Cross-Origin-Opener-Policy', 'unsafe-none'))
        response_headers.append(('Cross-Origin-Resource-Policy', 'cross-origin'))

        return Response(content, resp.status_code, response_headers)
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
