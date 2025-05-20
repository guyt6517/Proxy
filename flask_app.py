from flask import Flask, request, Response
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote

app = Flask(__name__)

@app.route('/proxy')
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return "Missing url parameter", 400

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Referer': target_url
    }

    try:
        resp = requests.get(target_url, headers=headers, timeout=10)
        content_type = resp.headers.get('Content-Type', '')
        
        # Get response headers safely
        excluded = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        safe_headers = [(k, v) for k, v in resp.headers.items() if k.lower() not in excluded]
        safe_headers.append(('Access-Control-Allow-Origin', '*'))

        # Handle HTML rewriting
        if 'text/html' in content_type:
            soup = BeautifulSoup(resp.text, 'lxml')
            for tag in soup.find_all(['a', 'form', 'script', 'link', 'img']):
                attr = 'href' if tag.name != 'form' else 'action'
                if tag.has_attr(attr):
                    original = tag[attr]
                    absolute = urljoin(target_url, original)
                    tag[attr] = f"/proxy?url={quote(absolute)}"
            return Response(str(soup), resp.status_code, safe_headers)

        # Binary or non-HTML content
        return Response(resp.content, resp.status_code, safe_headers)

    except requests.exceptions.Timeout:
        return "Upstream site timed out", 504
    except Exception as e:
        return f"Error: {str(e)}", 500

