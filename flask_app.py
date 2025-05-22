from flask import Flask, request, Response, render_template_string, redirect
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote

app = Flask(__name__)

PROXY_PREFIX = "/proxy?url="

# HTML template for the main proxy page
PAGE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Simple Proxy</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 0; }
        .top-bar {
            display: flex;
            align-items: center;
            background: #222;
            padding: 10px;
            color: white;
        }
        input[type=text] {
            flex-grow: 1;
            padding: 6px;
            border-radius: 4px;
            border: none;
        }
        button {
            margin-left: 10px;
            padding: 6px 12px;
            border: none;
            border-radius: 4px;
            background: #007BFF;
            color: white;
            cursor: pointer;
        }
        iframe {
            width: 100%;
            height: calc(100vh - 50px);
            border: none;
        }
    </style>
</head>
<body>
    <form class="top-bar" action="/browse" method="get">
        <input type="text" name="url" placeholder="Enter URL to proxy..." value="{{ url or '' }}">
        <button type="submit">Go</button>
    </form>
    {% if url %}
    <iframe src="{{ proxy_url }}"></iframe>
    {% endif %}
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(PAGE_TEMPLATE)

@app.route('/browse')
def browse():
    url = request.args.get('url')
    if not url:
        return redirect('/')
    proxy_url = f"{PROXY_PREFIX}{quote(url)}"
    return render_template_string(PAGE_TEMPLATE, url=url, proxy_url=proxy_url)

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
        headers = {k: v for k, v in request.headers if k.lower() != 'host'}

        if request.method == 'POST':
            resp = requests.post(target_url, data=request.form, headers=headers, stream=True)
        else:
            resp = requests.get(target_url, headers=headers, stream=True)

        content_type = resp.headers.get('Content-Type', '')
        if 'text/html' in content_type:
            content = rewrite_html(resp.text, target_url)
            content = content.encode(resp.encoding or 'utf-8')
        else:
            content = resp.content

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(name, value) for (name, value) in resp.raw.headers.items()
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
