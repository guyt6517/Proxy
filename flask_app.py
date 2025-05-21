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
        headers_to_send = {k: v for k, v in request.headers if k.lower() != 'host'}

        if request.method == 'POST':
            resp = requests.post(target_url, data=request.form, headers=headers_to_send, allow_redirects=True)
        else:
            resp = requests.get(target_url, headers=headers_to_send, params=request.args, allow_redirects=True)

        content_type = resp.headers.get('Content-Type', '')

        # requests auto-decompresses content if stream=False (default)
        if 'text/html' in content_type:
            # Rewrite the HTML content and then encode to bytes
            rewritten = rewrite_html(resp.text, target_url)
            content = rewritten.encode('utf-8')
        else:
            content = resp.content

        # Exclude hop-by-hop and content-encoding headers
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(k, v) for k, v in resp.raw.headers.items() if k.lower() not in excluded_headers]

        # Add proxy-specific headers
        headers.append(('Access-Control-Allow-Origin', '*'))
        headers.append(('X-Frame-Options', 'ALLOWALL'))
        headers.append(('Content-Security-Policy', 'frame-ancestors *'))
        headers.append(('Cross-Origin-Embedder-Policy', 'unsafe-none'))
        headers.append(('Cross-Origin-Opener-Policy', 'unsafe-none'))
        headers.append(('Cross-Origin-Resource-Policy', 'cross-origin'))

        # Add/update Content-Length header to match the content length
        headers = [(k, v) for k, v in headers if k.lower() != 'content-length']
        headers.append(('Content-Length', str(len(content))))

        # Ensure Content-Type header exists (especially for rewritten HTML)
        if not any(k.lower() == 'content-type' for k, v in headers):
            headers.append(('Content-Type', content_type if content_type else 'application/octet-stream'))

        return Response(content, resp.status_code, headers)

    except Exception as e:
        return f"Proxy error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
