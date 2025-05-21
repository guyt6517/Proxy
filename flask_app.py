from flask import Flask, request, Response
import requests

app = Flask(__name__)

@app.route('/proxy')
def proxy():
    target_url = request.args.get('url')
    if not target_url:
        return "Missing url parameter", 400

    try:
        # Fetch the target URL
        resp = requests.get(target_url, stream=True)
        content_type = resp.headers.get('Content-Type', '')

        # Read content
        content = resp.content

        # Filter out hop-by-hop headers
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]

        # Add your CORS and framing headers
        headers.append(('Access-Control-Allow-Origin', '*'))
        headers.append(('X-Frame-Options', 'ALLOWALL'))
        headers.append(('Content-Security-Policy', 'frame-ancestors *'))
        headers.append(('Cross-Origin-Embedder-Policy', 'unsafe-none'))
        headers.append(('Cross-Origin-Opener-Policy', 'unsafe-none'))
        headers.append(('Cross-Origin-Resource-Policy', 'cross-origin'))
        headers.append(('Content-Type', content_type))

        return Response(content, resp.status_code, headers)
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
