import argparse
import socket
import sys
import struct
import json
import os
import logging


# https://stackoverflow.com/a/28950776
def get_router_assigned_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except:
            ip = None
    return ip


class Server:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.ip = self.ip_addr()
        self.configure_logger()

    def ip_addr(self):
        addr = get_router_assigned_ip()
        if addr:
            ipaddr = addr
        else:
            ipaddr = socket.gethostbyname(self.host)
        return ipaddr

    def configure_logger(self):
        self.logger = logging.getLogger(Server.__name__)
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        # TODO: add client ip and port to the formatter (extra parameter)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

    def run(self):
        try:
            while True:
                conn, addr = self.sock.accept()
                with conn:
                    while True:
                        # TODO: Handle the case when client disconnects
                        data = conn.recv(1024)
                        conn.sendall(b'Response: ' + data)

        except KeyboardInterrupt:
            print('\nExiting...')

    def __enter__(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen()
        print(f'Server up and running at {self.ip}:{self.port} ...')
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.sock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('port', help='Port in which the server is running', type=int)
    args = parser.parse_args()

    with Server(host='', port=args.port) as server:
        server.run()