from flask import Flask, request, Response
import requests

app = Flask(__name__)

@app.route('/proxy')
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return "Missing url parameter", 400

    try:
        # Fetch the content from the target URL
        resp = requests.get(target_url)
        
        # Build a response with the same content and content type
        excluded_headers = ['x-frame-options', 'content-security-policy','content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]

        # Add CORS headers
        headers.append(('Access-Control-Allow-Origin', '*'))

        return Response(resp.content, resp.status_code, headers)
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
