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
