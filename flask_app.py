from flask import Flask, request, Response
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import html
import logging

app = Flask(__name__)

# Setup logging to show DEBUG info
logging.basicConfig(level=logging.DEBUG)

PROXY_PREFIX = "https://proxy-made-with-pain.onrender.com/proxy?url="

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
                    element['action'] = proxied_url

    return str(soup)

@app.route('/proxy', methods=['GET', 'POST'])
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return "Missing url parameter", 400

    try:
        is_google_search = 'google.com/search' in target_url
        method = 'GET' if is_google_search else request.method

        headers = {k: v for k, v in request.headers if k.lower() != 'host'}

        if method == 'POST':
            resp = requests.post(target_url, data=request.form, headers=headers)
        else:
            resp = requests.get(target_url, headers=headers)

        # DEBUG LOGGING: headers and partial content
        app.logger.debug(f"Response headers from {target_url}: {resp.headers}")
        snippet = resp.content[:500]
        try:
            snippet_text = snippet.decode(resp.encoding or resp.apparent_encoding or 'utf-8', errors='replace')
        except Exception:
            snippet_text = repr(snippet)
        app.logger.debug(f"Response content snippet from {target_url}:\n{snippet_text}")

        content_type = resp.headers.get('Content-Type', '')
        if 'text/html' in content_type:
            encoding = resp.encoding or resp.apparent_encoding or 'utf-8'
            content = rewrite_html(resp.text, target_url)
            content = content.encode(encoding)
        else:
            content = resp.content

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(name, value) for (name, value) in resp.headers.items()
                            if name.lower() not in excluded_headers]

        response_headers.append(('Access-Control-Allow-Origin', '*'))
        response_headers.append(('X-Frame-Options', 'ALLOWALL'))
        response_headers.append(('Content-Security-Policy', 'frame-ancestors *'))
        response_headers.append(('Cross-Origin-Embedder-Policy', 'unsafe-none'))
        response_headers.append(('Cross-Origin-Opener-Policy', 'unsafe-none'))
        response_headers.append(('Cross-Origin-Resource-Policy', 'cross-origin'))
        response_headers.append(('Content-Type', content_type))

        return Response(content, resp.status_code, response_headers)

    except Exception as e:
        app.logger.error(f"Proxy error for URL '{target_url}': {str(e)}", exc_info=True)

        safe_error_msg = html.escape(str(e))

        error_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head><title>Proxy Error</title></head>
        <body>
            <h1>Proxy Error</h1>
            <p>An error occurred while processing your request:</p>
            <pre>{safe_error_msg}</pre>
            <script>
                console.error("Proxy error for URL: {target_url}");
                console.error("Error message: {safe_error_msg}");
            </script>
        </body>
        </html>
        """
        return Response(error_html, status=500, content_type='text/html')

if __name__ == '__main__':
    app.run(debug=True)
