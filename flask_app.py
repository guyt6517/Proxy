from flask import Flask, request, Response, session
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # replace with a strong secret

PROXY_PREFIX = "https://proxy-made-with-pain.onrender.com/proxy?url="

# Store user sessions here (in-memory; for production use persistent storage)
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

@app.route('/proxy', methods=['GET', 'POST'])
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return "Missing url parameter", 400

    try:
        user_sess = get_user_session()
        method = request.method

        # Forward headers except Host and Cookie (cookies handled by user_sess)
        headers = {k: v for k, v in request.headers if k.lower() not in ['host', 'cookie']}

        if method == 'POST':
            resp = user_sess.post(target_url, headers=headers, data=request.form)
        else:
            resp = user_sess.get(target_url, headers=headers, params=request.args)

        content_type = resp.headers.get('Content-Type', '')
        if 'text/html' in content_type:
            content = rewrite_html(resp.text, target_url)
            content = content.encode(resp.encoding or 'utf-8')
        else:
            content = resp.content

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]

        # Add your CORS and framing headers
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
