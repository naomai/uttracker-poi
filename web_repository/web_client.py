from  http.client import HTTPConnection, HTTPSConnection, HTTPResponse
from urllib.parse import urlparse

class WebClient:
    __client = None
    __path: str
    __response: HTTPResponse
    __headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0) UTTracker/UnrealPOI/ContentDownloader (+https://github.com/naomai/uttracker-downloader)",
        }
    __requests_left: int = 1
    __url: str

    def __init__(self, url: str):
        self.__set_request_url(url)

    def request(self, method: str="GET", body: str|bytes = None):
        while self.__requests_left > 0:
            print(self.__url)
            self.__client.request(method, self.__path, body, self.__headers)
            response = self.__client.getresponse()
            self.__response = response
    
            url_redirect = response.headers.get("Location")
            if url_redirect and response.status >= 300 and response.status <= 399:
               self.__headers['Referer'] = self.__url
               self.__set_request_url(url_redirect)
               self.__requests_left = self.__requests_left - 1
            else:
                break

        return self

    def get(self):
        return self.request("GET")

    def post(self, body: str|bytes = None, contentType: str = "application/octet-stream"):
        self.__headers['Content-Length'] = len(body)
        self.__headers['Content-Type'] = contentType
        return self.request("POST", body)
    
    def follow(self, count: str=5):
        self.__requests_left = count + 1
        return self
    

    def status(self):
        return self.__response.status
    
    def body(self):
        return self.__response.read()
    
    def __set_request_url(self, url: str):
        url_parsed = urlparse(url)

        if url_parsed.scheme == "http":
            self.__client = HTTPConnection(url_parsed.hostname, url_parsed.port, timeout=10)
        elif url_parsed.scheme == "https":
            self.__client = HTTPSConnection(url_parsed.hostname, url_parsed.port, timeout=10)

        path = url_parsed.path
        if url_parsed.query:
            path = path + "?" + url_parsed.query
        self.__path = path
        self.__url = url