from flask import Flask, request, Response, session #PIP
import requests #PIP
from bs4 import BeautifulSoup #PIP
from urllib.parse import urljoin, quote, unquote, urlparse
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-key')

http_session = requests.Session()

def rewrite_html(content, base_url):
    soup = BeautifulSoup(content, 'html.parser')

    tags = {
        'a': 'href',
        'img': 'src',
        'script': 'src',
        'link': 'href',
        'iframe': 'src',
        'source': 'src',
        'form': 'action'
    }

    for tag, attr in tags.items():
        for element in soup.find_all(tag):
            if element.has_attr(attr):
                original = urljoin(base_url, element[attr])
                proxied = f"/proxy?url={quote(original)}"
                element[attr] = proxied

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
    
    target_url = unquote(target_url)

    try:
        method = request.method
        headers = {k: v for k, v in request.headers if k.lower() != 'host'}
        data = request.form if method == 'POST' else None
        if method == 'POST':
            resp = http_session.post(target_url, headers = headers, data = data, allow_redirects=True)
        else: 
            resp = http_session.get(target_url, headers = headers, params = request.args, allow_redirects=True)
        
        content_type = resp.headers.get('Content-Type', '')

        #if HTML, it rewrites URLs
        if 'text/html' in content_type:
            content = rewrite_html(resp.text, target_url)
        else:
            content = resp.content
        
        #Build headers
        excluded = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(k, v) for k, v in resp.raw.headers.items() if k.lower() not in excluded]
        headers.append(('Access-Control-Allow-Origin', '*'))
        headers.append(('Content-Type', content_type))
        headers.append(('X-Frame-Options', 'ALLOWALL'))
        headers.append(('Content-Security-Policy', "frame-ancestors *"))
        headers.append(('Cross-Origin-Embedder-Policy', 'unsafe-none'))
        headers.append(('Cross-Origin-Opener-Policy', 'unsafe-none'))
        headers.append(('Cross-Origin-Resource-Policy', 'cross-origin'))

        return Response(content, resp.status_code, headers)
    except Exception as e:
        return f"Proxy error: {str(e)}"
