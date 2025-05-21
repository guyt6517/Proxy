import os
from flask import Flask, request, Response, session
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote, unquote, urlparse

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
            resp = http_session.post(target_url, headers=headers, data=data, allow_redirects=True)
        else:
            resp = http_session.get(target_url, headers=headers, params=request.args, allow_redirects=True)
        
        content_type = resp.headers.get('Content-Type', '')

        # Fix encoding if needed
        if resp.encoding is None:
            resp.encoding = 'utf-8'  # default to utf-8 if unknown

        # If HTML, rewrite URLs
        if 'text/html' in content_type:
            content = rewrite_html(resp.text, target_url)
        else:
            content = resp.content

        # Exclude headers that should not be forwarded
        excluded = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(k, v) for k, v in resp.raw.headers.items() if k.lower() not in excluded]

        # Ensure Content-Type includes charset for HTML
        if 'text/html' in content_type:
            if not any('charset' in v.lower() for (k, v) in response_headers if k.lower() == 'content-type'):
                response_headers.append(('Content-Type', 'text/html; charset=utf-8'))
        else:
            response_headers.append(('Content-Type', content_type))

        # Add CORS and frame headers
        response_headers.append(('Access-Control-Allow-Origin', '*'))
        response_headers.append(('X-Frame-Options', 'ALLOWALL'))
        response_headers.append(('Content-Security-Policy', 'frame-ancestors *'))
        response_headers.append(('Cross-Origin-Embedder-Policy', 'unsafe-none'))
        response_headers.append(('Cross-Origin-Opener-Policy', 'unsafe-none'))
        response_headers.append(('Cross-Origin-Resource-Policy', 'cross-origin'))

        return Response(content, resp.status_code, response_headers)
    except Exception as e:
        return f"Proxy error: {str(e)}"

if __name__ == "__main__":
    app.run(debug=True)
