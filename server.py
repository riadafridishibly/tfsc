#!/usr/bin/env python

import argparse
import socket
import sys
import struct
import json
import os
import logging
from typing import Tuple, Optional, Dict, Any

AddrType = Tuple[str, int]

BUFFER_SIZE = 65535


class Status:
    OK = 0
    ERROR = 1


class Method:
    LIST = 'LIST'
    GET = 'GET'
    PUT = 'PUT'


def get_router_assigned_ip() -> Optional[str]:
    # https://stackoverflow.com/a/28950776

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
        except:
            ip = None
    return ip


def secure_filename(filename: str) -> str:
    for sep in os.path.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, ' ')
            filename = '_'.join(filename.split()).strip('_.')
    return filename


class Server:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.ip = self.ip_addr()
        self.configure_logger()
        self.start()

    def ip_addr(self) -> str:
        addr = get_router_assigned_ip()
        if addr:
            ipaddr = addr
        else:
            ipaddr = socket.gethostbyname(self.host)
        return ipaddr

    # ------------------- utility -------------------
    def read_from_socket(self, sock: socket.socket, size: int) -> bytes:
        data = bytearray()
        while len(data) < size:
            # this sock.recv() call can also fail
            packet = sock.recv(size - len(data))
            if not packet:
                break
            data.extend(packet)
        return bytes(data)

    def read_header(self, sock: socket.socket, addr: AddrType) -> Optional[dict]:
        try:
            size = struct.unpack('>H', sock.recv(2))[0]
            data = self.read_from_socket(sock, size=size)
            return json.loads(data)
        except struct.error:
            self.err_log('Could not extract the header', addr=addr)
            return None

    def generate_header(
            self,
            status: int,
            content_length: int,
            encoding: str = 'utf-8',
            filename: str = None) -> bytes:
        header = {
            'status': status,
            'content-length': content_length,
            'encoding': encoding,
        }
        if filename:
            header['filename'] = filename

        encoded_header = json.dumps(header).encode('utf-8')
        return struct.pack('>H', len(encoded_header)) + encoded_header

    def send_error_msg(self, msg: str, sock: socket.socket, addr: AddrType):
        encoded_msg = msg.encode('utf-8')
        header = self.generate_header(
            status=Status.ERROR,
            content_length=len(encoded_msg),
            encoding='utf-8'
        )
        try:
            sock.sendall(header + encoded_msg)
        except Exception as e:
            self.err_log(str(e), addr=addr)

    # ------------------ handlers -------------------
    def list_handler(self, sock: socket.socket, addr: AddrType):
        files = (f for f in os.listdir(b'.') if os.path.isfile(f))
        data = b'\n'.join(files)
        header = self.generate_header(
            status=Status.OK, content_length=len(data))

        try:
            sock.sendall(header + data)
            self.info_log(f"{'LIST'} - OK - ", addr=addr)
        except Exception as e:
            self.err_log(str(e), addr=addr)

    def get_handler(self, sock: socket.socket, addr: AddrType, header: dict):
        filename = secure_filename(str(header.get('filename')))

        if os.path.isfile(filename):
            file_len = os.path.getsize(filename)
            response_header = self.generate_header(
                status=Status.OK, content_length=file_len, encoding='binary', filename=filename)
            sock.sendall(response_header)

            with open(filename, 'rb') as f:
                while file_len > 0:
                    data = f.read(BUFFER_SIZE)
                    if not data:
                        break
                    try:
                        sock.sendall(data)
                        file_len -= len(data)
                    except ConnectionResetError:
                        self.info_log(
                            f"{'GET'} {filename} - Error - Client Disconnected", addr=addr)
                        return

            self.info_log(f"{'GET'} {filename} - OK -", addr=addr)

        else:
            self.send_error_msg(f'File not found "{filename}"', sock, addr)
            self.err_log(f"{'GET'} - Error - File not found", addr=addr)

    def put_handler(self, sock: socket.socket, addr: Tuple[str, int], header: dict):
        filename = secure_filename(header.get('filename'))

        if os.path.exists(filename):
            message = f'File Exists: "{filename}"'
            self.send_error_msg(message, sock, addr)
            self.err_log(f"PUT - Error - {message}", addr=addr)
            return

        success_header = self.generate_header(status=Status.OK, content_length=0)
        # this call can fail
        sock.sendall(success_header)

        content_len = header.get('content-length')

        if content_len == 0:
            self.err_log('Ignoring zero sized file', addr=addr)
            return None

        n = 0
        with open(filename, 'wb') as f:
            while n < content_len:
                data = sock.recv(BUFFER_SIZE)
                if not data:
                    break
                n += f.write(data)

        self.info_log(f"{'PUT'} {filename} - OK -", addr=addr)


    # ------------------- logging -------------------
    def configure_logger(self):
        TIME_FORMAT = "%d/%b/%y %H:%M:%S"
        FORMAT = '%(clientaddr)s - %(asctime)-15s - %(message)s'
        logging.basicConfig(format=FORMAT, datefmt=TIME_FORMAT)
        self.logger = logging.getLogger(type(self).__name__.lower())
        self.logger.setLevel(logging.INFO)

    def client_info(self, addr):
        return {'clientaddr': addr[0] + ':' + str(addr[1])}

    def err_log(self, msg, addr):
        self.logger.error(msg, extra=self.client_info(addr))

    def info_log(self, msg, addr):
        self.logger.info(msg, extra=self.client_info(addr))

    # ------------------- control -------------------
    def start(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen()
        print(f'Server up and running at {self.ip}:{self.port} ...')

    def run(self):
        try:
            while True:
                conn, addr = self.sock.accept()
                with conn:
                    header = self.read_header(conn, addr)
                    if header:
                        if header.get('method') == Method.LIST:
                            self.list_handler(conn, addr)
                        elif header.get('method') == Method.GET:
                            self.get_handler(conn, addr, header)
                        elif header.get('method') == Method.PUT:
                            self.put_handler(conn, addr, header)
                        else:
                            self.err_log('Method Unknown', addr=addr)
                    else:
                        self.send_error_msg(
                            'send request with a header, see documentation.', conn, addr)

        except KeyboardInterrupt:
            print('\nExiting...')

    def close(self):
        self.sock.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'port', help='Port in which the server is running', type=int)
    args = parser.parse_args()

    with Server(host='', port=args.port) as server:
        server.run()
