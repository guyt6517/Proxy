from flask import Flask, request, Response
import requests

app = Flask(__name__)

@app.route('/proxy')
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return "Missing url parameter", 
    if True:
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
ChatGPT said:
Your script seems to be an incomplete and malformed attempt at creating a proxy endpoint using Flask. Here are a few issues and a corrected version:

Issues:
You never make a request to the target URL. You're using resp without defining it.

The content and content_type variables are undefined.

The try block is missing — there’s an except without a try.

Misuse of if True: — probably intended to be part of a try block.

Corrected Version:
from flask import Flask, request, Response
import requests

app = Flask(__name__)

@app.route('/proxy')
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return "Missing url parameter", 400

    try:
        # Make the request to the target URL
        resp = requests.get(target_url, stream=True)

        # Filter headers
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]

        # Add CORS and security headers
        headers.append(('Access-Control-Allow-Origin', '*'))
        headers.append(('Content-Type', resp.headers.get('Content-Type', 'text/plain')))
        headers.append(('X-Frame-Options', 'ALLOWALL'))
        headers.append(('Content-Security-Policy', "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:;"))
        headers.append(('Cross-Origin-Embedder-Policy', 'require-corp'))

        return Response(resp.content, resp.status_code, headers)
    except Exception as e:
        return str(e), 500
Note:
This proxy is not secure for public deployment. Anyone could use it to bypass CORS or access arbitrary URLs.

Consider implementing URL whitelisting and rate limiting for production use.

Let me know if you want a version that supports POST or other methods.

You said:
I want to bypass cors with it
ChatGPT said:
Got it — using a proxy like this is a common way to bypass CORS restrictions during development or when working with third-party APIs that don't send the correct CORS headers.

Here's what this proxy does for CORS:
It fetches the target URL server-side (so CORS doesn't apply).

Then it responds to the browser with CORS headers, like Access-Control-Allow-Origin: *.

This bypasses browser CORS enforcement because the browser thinks the response is from your own server, not the original third-party site.

Secure, working CORS-bypass proxy with support for GET and POST:
from flask import Flask, request, Response
import requests

app = Flask(__name__)

@app.route('/proxy', methods=['GET', 'POST'])
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return "Missing url parameter", 400

    try:
        if request.method == 'POST':
            resp = requests.post(target_url, data=request.form or request.data, headers=request.headers)
        else:
            resp = requests.get(target_url, headers=request.headers, params=request.args)

        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]

        # Add CORS headers
        headers.append(('Access-Control-Allow-Origin', '*'))
        headers.append(('Access-Control-Allow-Headers', '*'))
        headers.append(('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'))
        headers.append(('Content-Type', resp.headers.get('Content-Type', 'text/plain')))

        return Response(resp.content, resp.status_code, headers)
    except Exception as e:
        return str(e), 500
