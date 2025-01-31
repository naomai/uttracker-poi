import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import threading
#from .ContentDownloader.LinkStore import LinkStore
#from .ContentDownloader import Downloader

store = None
downloader = None
ENDPOINT_PACKAGE_DOWNLOAD = "/download"
serverThread = None
httpServer = None

def handlePackageDownload(postData):
    try:
        request = json.loads(postData)
    except json.decoder.JSONDecodeError:
        raise ValueError("Invalid request data")
        
    if 'package' in request:
        package = request['package']
        (url, fileName) = store.getPackageLinkInfo(request['package'])

        if downloader.isDownloaded(fileName):
            return {'status': 'Already downloaded'}
        
        downloader.download(url, fileName)
        return {'status': "Download started..."}



class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server_class):
        self.server_class = server_class
        super().__init__(request, client_address, server_class)

    def do_GET(self):
        response = {"error": "This GET request is not supported by the service"}
        response = handlePackageDownload("{\"package\":\"MH-AfterDark\"}")
        self.send_response(405)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-length", str(len(json.dumps(response))))
        self.end_headers()
        self.wfile.write(str(response).encode('utf8'))
        

    def do_POST(self):
        bytes = int(self.headers['Content-length'])
        postData = self.rfile.read(bytes)

        response = {'error': 'Requested resource was not found'}
        status = 404
        try:
            if self.path == ENDPOINT_PACKAGE_DOWNLOAD:
                response = handlePackageDownload(postData)
                status = 200
        except ValueError as e:
            response = {'error': str(e)}
            status = 400
        except Exception as e:
            response = {'error': "Internal server error: " + str(e)}
            status = 500

        self.send_response(status)
        responseEncoded = json.dumps(response)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(responseEncoded)))
        self.end_headers()

        self.wfile.write(str(response).encode('utf8'))


def init(addr, port):
    global serverThread, httpServer
    

    serverAddress = (addr, port)
    httpServer = HTTPServer(serverAddress, RequestHandler)

    #serverThread = threading.Thread(target=serve)
    #serverThread.start()
    serve()


def serve():
    httpServer.serve_forever()