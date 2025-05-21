
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
