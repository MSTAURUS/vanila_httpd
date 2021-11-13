#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import re
import datetime
import mimetypes
from urllib.parse import urlparse, unquote
from concurrent.futures import ThreadPoolExecutor
import socket
import logging
import sys
import multiprocessing as mp
import threading
from pathlib import Path


OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
METHOD_NOT_ALLOWED = 405


HOST = "localhost"
PORT = 8080
DOCUMENT_ROOT = "."
WORKERS = 6
LOG = "httpd.log"
MAX_CONNECT = 100

CONTENT_TYPES = {
    "html": "text/html",
    "css": "text/css",
    "js": "application/javascript",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "swf": "application/x-shockwave-flash",
    "txt": "text/html"
}


class HTTPRequest:
    def __init__(self, request, document_root):
        self.request = request
        self.root = document_root
        self.available_methods = {"GET", "HEAD"}
        self.method = None
        self.uri = None
        self.uri_path = None
        self.protocol = None
        self.headers = {}
        self.response_code = None
        self.body = None
        self.sep_index = 0
        self.parse_request()
        self.normalize_uri()

    def parse_start_line(self):
        starting_line = self.request.split("\r\n")[0]
        self.method, self.uri, self.protocol = starting_line.split(" ")[0:3]

    def parse_headers(self):
        another_lines = self.request.split("\r\n")[1:]
        self.sep_index = 0
        j = 0
        for i in another_lines:
            if i == "":
                self.sep_index = j
                break
            header = i.split(": ")[0]
            value = "".join(i.split(": ")[1:])
            self.headers[header] = value
            j += 1

    def parse_body(self):
        self.body = "".join(self.request.split("\r\n")[1:][self.sep_index + 1:])

    def parse_request(self):
        self.parse_start_line()
        self.parse_headers()
        self.parse_body()

    def normalize_uri(self):
        self.uri = self.uri.split("?")[0].split("#")[0]
        regexp = r"^\/[\/\.a-zA-Z0-9\-\_\%]+$"

        if re.match(regexp, self.uri):
            self.uri_path = Path(self.root + unquote(self.uri))

        if self.uri.endswith("/"):
            if self.uri_path:
                self.uri_path = Path(self.uri_path, "index.html")
            else:
                self.uri_path = Path(self.root, "index.html")

    def validate_method(self):
        if self.method not in self.available_methods:
            self.response_code = METHOD_NOT_ALLOWED
        else:
            self.response_code = OK

    def validate_uri(self):
        root = Path.cwd() if self.root == "." else Path(self.root)
        uri = Path(root, self.uri_path).resolve()
        if self.uri_path is None:
            self.response_code = NOT_FOUND
        elif not Path.exists(self.uri_path):
            self.response_code = NOT_FOUND
        elif root not in uri.parents:
            self.response_code = FORBIDDEN


class HTTPResponse:
    reply_values = {
        OK: "OK",
        BAD_REQUEST: "Bad request",
        FORBIDDEN: "Forbidden",
        NOT_FOUND: "Not Found",
        METHOD_NOT_ALLOWED: "Method Not Allowed",
    }

    def __init__(self, request):
        self.code = request.response_code
        self.method = request.method
        self.body = None
        self.type = None

    def set_body(self, file_path):
        try:
            file = open(file_path, "rb")
            self.body = file.read()
            file.close()
            file_type = Path(file_path).suffix[1:]
            try:
                self.type = CONTENT_TYPES[file_type]
            except:
                # RFC 2046 states in section 4.5.1:
                self.type = "application/octet-stream"
        except:
            logging.info("Error while reading file: {}".format(file_path))
            self.body = "".encode("utf-8")

    def create_response(self):
        response = "HTTP/1.1 {} {}\r\n".format(self.code, self.reply_values[self.code])
        response += "Date: {}\r\n".format(
            datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S")
        )
        response += "Server: my_httpd\r\n"
        response += "Allow: GET, HEAD\r\n"
        response += "Content-Length: {}\r\n".format(
            len(self.body) if self.body is not None and self.method in ["GET", "HEAD"] else 0
        )
        if self.type:
            response += "Content-Type: {}\r\n".format(self.type)
        response += "\r\n"

        if self.method and self.method == "GET":
            response = response.encode() + self.body
        else:
            response = response.encode()

        return response


class HTTPServer:
    def __init__(
        self, host="", port=8080, document_root="", workers=4, max_connections=4
    ):
        self.host = host
        self.port = int(port)
        self.document_root = document_root
        self.workers = int(workers)
        self.running_workers = []
        self.max_connections = max_connections
        self.batch_size = 4096
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(self.max_connections)
        logging.info("Starting http server ")

    def stop(self):
        self.server.shutdown(socket.SHUT_RDWR)
        logging.info("Http server stopped")

    def handle_request(self, client_socket, client_address):
        request = HTTPRequest(self.receive(client_socket), self.document_root)
        request.validate_method()
        request.validate_uri()
        logging.info("Request from {}:{}".format(client_address[0], client_address[1]))

        response = HTTPResponse(request)
        response.set_body(request.uri_path)

        response_data = response.create_response()
        try:
            client_socket.sendall(response_data)
        except ConnectionError as e:
            logging.error("Request handle error: {}").format(e)
        finally:
            client_socket.close()

    def receive(self, client_socket):
        data = ""
        while True:
            batch = client_socket.recv(self.batch_size)
            if batch == b"":
                logging.error("Socket connection wrong")
                break
            data += batch.decode("utf-8")
            if "\r\n\r\n" in data:
                break
        return data

    def listen(self):
        while True:
            client_socket, client_address = self.server.accept()
            logging.info(
                "Connection with: {}:{}".format(client_address[0], client_address[1])
            )
            client_handler = threading.Thread(
                target=self.handle_request, args=(client_socket, client_address)
            )
            client_handler.start()

    def start_workers(self):
        self.running_workers = []
        for i in range(self.workers):
            worker = mp.Process(target=self.listen, name="WORKER_{}".format(i + 1))
            self.running_workers.append(worker)
            worker.start()
            logging.info("Worker {} is created".format(worker.name))
        for w in self.running_workers:
            w.join()

    def shutdown_workers(self):
        for w in self.running_workers:
            w.terminate()
            logging.info("Worker {} shutdown".format(w.name))


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--host", dest="host", default=HOST)
    args.add_argument("--port", dest="port", default=PORT)
    args.add_argument("-r", dest="document_root", default=DOCUMENT_ROOT)
    args.add_argument("-w", dest="workers", default=WORKERS)
    args.add_argument("-c", dest="max_connect", default=MAX_CONNECT)
    args.add_argument("--log", dest="log", default=LOG)

    args = args.parse_args()

    logging.basicConfig(
        filename=args.log,
        level=logging.INFO,
        format="[%(asctime)s] %(levelname).1s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
    )

    try:
        server = HTTPServer(
            args.host, args.port, args.document_root, args.workers, args.max_connect
        )
        server.start()
        logging.info("Starting server at %s:%s" % (args.host, str(args.port)))
        print("Starting server at %s:%s" % (args.host, str(args.port)))
    except Exception as e:
        logging.error("Error on start server. Error: {}".format(e))
        print("Error on start server. Error: {}".format(e))
        sys.exit()

    try:
        server.start_workers()
    except KeyboardInterrupt:
        server.shutdown_workers()
    except Exception as e:
        server.shutdown_workers()
        logging.error("Error on {}".format(e))
    finally:
        server.stop()


if __name__ == "__main__":
    main()
