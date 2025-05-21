from flask import Flask, request, Response
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

@app.route('/proxy')
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return "Missing url parameter", 400

    try:
        # Fetch the content
        resp = requests.get(target_url)
        content_type = resp.headers.get('Content-Type', '')

        content = resp.content

        # If it's HTML, parse and strip <script> and <meta http-equiv="refresh">
        if 'text/html' in content_type:
            soup = BeautifulSoup(content, 'html.parser')

            # Remove all <script> tags
            for script in soup.find_all('script'):
                script.decompose()

            # Remove <meta http-equiv="refresh">
            for meta in soup.find_all('meta', attrs={'http-equiv': True}):
                if meta['http-equiv'].lower() == 'refresh':
                    meta.decompose()

            content = str(soup).encode('utf-8')

        # Build response
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]

        # Add CORS header
        headers.append(('Access-Control-Allow-Origin', '*'))
        headers.append(('Content-Type', content_type))
        headers.append(('x-frame-options', '*'))
        headers.append(('content-security-policy', '*'))
        headers.append(('cross-origin-embedder-policy', '*'))
        return Response(content, resp.status_code, headers)
    except Exception as e:
        return str(e), 500
@app.route('/ip')
