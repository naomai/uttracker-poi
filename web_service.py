from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading
from content_downloader import link_lookup
from urllib.parse import urlparse

store = None
ENDPOINT_MAP_DOWNLOAD = "/download"
__server_thread = None
__http_server = None

def handle_map_download(postData):
    try:
        request = json.loads(postData)
    except json.decoder.JSONDecodeError:
        raise ValueError("Invalid request data")
        
    if 'map' in request:
        package = request['map']
        response = {'status': "Download request successful"}

        # delegate link lookup to main thread
        link_lookup.request(package)

        return response
    
class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server_class):
        self.server_class = server_class
        super().__init__(request, client_address, server_class)

    def do_GET(self):
        response = {"error": "This GET request is not supported by the service"}

        self.send_response(405)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-length", str(len(json.dumps(response))))
        self.end_headers()
        self.wfile.write(str(response).encode('utf8'))
        

    def do_POST(self):
        bytes = int(self.headers['Content-length'])
        post_data = self.rfile.read(bytes)

        response = {'error': 'Requested resource was not found'}
        status = 404
        try:
            if self.path == ENDPOINT_MAP_DOWNLOAD:
                response = handle_map_download(post_data)
                status = 200
        except ValueError as e:
            response = {'error': str(e)}
            status = 400
        except Exception as e:
            response = {'error': "Internal server error: " + str(e)}
            status = 500

        self.send_response(status)
        response_encoded = json.dumps(response)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_encoded)))
        self.end_headers()

        self.wfile.write(response_encoded.encode('utf8'))


def init(addr, port):
    global __server_thread, __http_server
    

    server_address = (addr, port)
    __http_server = HTTPServer(server_address, RequestHandler)

    __server_thread = threading.Thread(target=serve)
    __server_thread.start()
    #serve()


def serve():
    __http_server.serve_forever()