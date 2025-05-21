from flask import Flask, request, Response
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote, unquote

app = Flask(__name__)

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
            if element.has_attr(attr):
                original_url = urljoin(base_url, element[attr])
                proxied_url = f"/proxy?url={quote(original_url)}"
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

    target_url = unquote(target_url)

    try:
        # Support POST and GET requests for proxying forms, etc.
        if request.method == 'POST':
            resp = requests.post(target_url, data=request.form, headers={k: v for k, v in request.headers if k.lower() != 'host'}, allow_redirects=True)
        else:
            resp = requests.get(target_url, headers={k: v for k, v in request.headers if k.lower() != 'host'}, params=request.args, allow_redirects=True)

        content_type = resp.headers.get('Content-Type', '')

        # Fix encoding if unknown
        if resp.encoding is None:
            resp.encoding = 'utf-8'

        if 'text/html' in content_type:
            content = rewrite_html(resp.text, target_url)
        else:
            content = resp.content

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]

        # Add CORS and framing headers
        headers.append(('Access-Control-Allow-Origin', '*'))
        headers.append(('X-Frame-Options', 'ALLOWALL'))
        headers.append(('Content-Security-Policy', 'frame-ancestors *'))
        headers.append(('Cross-Origin-Embedder-Policy', 'unsafe-none'))
        headers.append(('Cross-Origin-Opener-Policy', 'unsafe-none'))
        headers.append(('Cross-Origin-Resource-Policy', 'cross-origin'))

        # Ensure Content-Type header is present and correct
        if 'text/html' in content_type and not any(k.lower() == 'content-type' for k, v in headers):
            headers.append(('Content-Type', 'text/html; charset=utf-8'))
        elif not any(k.lower() == 'content-type' for k, v in headers):
            headers.append(('Content-Type', content_type))

        return Response(content, resp.status_code, headers)

    except Exception as e:
        return f"Proxy error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
