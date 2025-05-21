from flask import Flask, request, Response
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote

app = Flask(__name__)

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
                # Resources: keep absolute URL, no proxy
                element[attr] = absolute_url
            elif tag in ['a', 'form']:
                # Links and forms: proxy via your proxy URL
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
        is_google_search = 'google.com/search' in target_url
        method = 'GET' if is_google_search else request.method

        headers = {k: v for k, v in request.headers if k.lower() != 'host'}

        if method == 'POST':
            resp = requests.post(target_url, data=request.form, headers=headers)
        else:
            resp = requests.get(target_url, headers=headers)

        content_type = resp.headers.get('Content-Type', '')
        if 'text/html' in content_type:
            content = rewrite_html(resp.text, target_url)
            content = content.encode(resp.encoding or 'utf-8')
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

        content_encoding = resp.headers.get('Content-Encoding', '')
        if content_encoding:
            response_headers.append(('Content-Encoding', content_encoding))

        return Response(content, resp.status_code, response_headers)
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
