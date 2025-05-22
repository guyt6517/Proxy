from flask import Flask, request, Response, redirect
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import html
import logging
import gzip
import zlib

app = Flask(__name__)
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
            elif tag == 'a':
                proxied_url = PROXY_PREFIX + quote(absolute_url)
                element[attr] = proxied_url
            elif tag == 'form':
                method = element.get('method', '').lower()
                if method not in ['get', 'post']:
                    element['method'] = 'get'

                element['action'] = '/proxy'

                hidden_input = soup.new_tag('input', attrs={
                    'type': 'hidden',
                    'name': 'url',
                    'value': absolute_url
                })
                element.insert(0, hidden_input)

    return str(soup)

@app.route('/proxy', methods=['GET', 'POST'])
def proxy():
    target_url = request.args.get('url') or request.form.get('url')
    if not target_url:
        return "Missing url parameter", 400

    try:
        is_google_search = 'google.com/search' in target_url
        method = 'GET' if is_google_search else request.method

        headers = {k: v for k, v in request.headers if k.lower() != 'host'}
        headers['Accept-Encoding'] = 'identity'
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'

        if method == 'POST':
            resp = requests.post(target_url, data=request.form, headers=headers)
        else:
            resp = requests.get(target_url, headers=headers, params=request.args)

        content_encoding = resp.headers.get('Content-Encoding', '')
        content_type = resp.headers.get('Content-Type', '')
        app.logger.debug(f"Content-Encoding: {content_encoding}")
        app.logger.debug(f"Content-Type: {content_type}")

        content = resp.content
        if content_encoding in ['gzip', 'x-gzip']:
            try:
                content = gzip.decompress(content)
            except Exception as e:
                app.logger.warning(f"Failed gzip decompress: {e}")
        elif content_encoding == 'deflate':
            try:
                content = zlib.decompress(content)
            except Exception:
                try:
                    content = zlib.decompress(content, -zlib.MAX_WBITS)
                except Exception as e:
                    app.logger.warning(f"Failed deflate decompress: {e}")

        if 'text/html' in content_type:
            encoding = resp.encoding or resp.apparent_encoding or 'utf-8'
            text_content = content.decode(encoding, errors='replace')

            soup = BeautifulSoup(text_content, 'html.parser')
            captcha_form = soup.find('form', id='captcha-form')
            if captcha_form:
                try:
                    q_token = captcha_form.find("input", {"name": "q"})["value"]
                    continue_url = captcha_form.find("input", {"name": "continue"})["value"]
                    action_path = captcha_form.get("action") or target_url
                    submit_url = urljoin(target_url, action_path)

                    payload = {
                        "q": q_token,
                        "continue": continue_url
                    }

                    captcha_resp = requests.post(submit_url, data=payload, headers=headers, allow_redirects=False)
                    if 300 <= captcha_resp.status_code < 400 and "Location" in captcha_resp.headers:
                        return redirect(captcha_resp.headers["Location"])
                    else:
                        return Response(captcha_resp.content, captcha_resp.status_code)
                except Exception as e:
                    app.logger.warning(f"Failed CAPTCHA form submission: {e}")

            rewritten = rewrite_html(text_content, target_url)
            content = rewritten.encode('utf-8')
            content_type = 'text/html; charset=utf-8'

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
