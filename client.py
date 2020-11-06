#!/usr/bin/env python

import socket
import struct
import sys
import json
import argparse
import os
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


class HeaderField:
    STATUS = 'status'
    METHOD = 'method'
    CONTENT_LEN = 'content-length'
    ENCODING = 'encoding'
    FILENAME = 'filename'


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def generate_header(
        method: str,
        content_length: int = 0,
        encoding: str = 'utf-8',
        filename: str = None) -> bytes:
    header = {
        HeaderField.METHOD: method,
        HeaderField.ENCODING: encoding,
    }

    if content_length:
        header[HeaderField.CONTENT_LEN] = content_length
    if filename:
        header[HeaderField.FILENAME] = filename

    encoded_header = json.dumps(header).encode('utf-8')
    return struct.pack('>H', len(encoded_header)) + encoded_header


def read_from_socket(sock: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            break
        data.extend(packet)
    return bytes(data)


def read_header(sock: socket.socket) -> Optional[dict]:
    try:
        size = struct.unpack('>H', sock.recv(2))[0]
        data = read_from_socket(sock, size=size)
        return json.loads(data)
    except struct.error:
        return None


def handle_list(sock: socket.socket):
    # send request
    header = generate_header(method=Method.LIST)
    sock.sendall(header)

    # recieve response
    received_header = read_header(sock)
    content_len = received_header.get(HeaderField.CONTENT_LEN)
    data = read_from_socket(sock, content_len)
    print(data.decode(received_header.get(HeaderField.ENCODING)))


def handle_get(sock: socket.socket, filename: str):
    # send request
    header = generate_header(
        method=Method.GET, encoding='binary', filename=filename)
    sock.sendall(header)

    # recieve response
    received_header = read_header(sock)
    status = received_header.get(HeaderField.STATUS)
    content_len = received_header.get(HeaderField.CONTENT_LEN)

    # handle server side error, can't get the file, exit
    if status != Status.OK:
        data = read_from_socket(sock, content_len).decode(
            received_header.get(HeaderField.ENCODING))
        eprint(data)
        return None

    # server is sending the file
    filename = received_header.get(HeaderField.FILENAME)

    # whether you should override the existing file
    # I don't know yet whether it's the correct approach to this problem
    if os.path.isfile(filename):
        eprint('File Exists:', filename)
        return None

    n = 0
    with open(filename, 'wb') as f:
        while n < content_len:
            data = sock.recv(BUFFER_SIZE)
            if not data:
                break
            n += f.write(data)


def handle_put(sock, filename):
    try:
        stat = os.stat(filename)
        header = generate_header(
            content_length=stat.st_size, method='put', filename=filename, encoding='binary')
        sock.sendall(header)

        header = read_header(sock)

        if header.get('status') != 0:
            message = read_from_socket(sock, header.get(
                'content-length')).decode(header.get('encoding'))
            print(message)
            return None

        with open(filename, 'rb') as f:
            file_len = stat.st_size
            while file_len > 0:
                data = f.read(4096)
                if not data:
                    break
                sock.send(data)
                file_len -= len(data)
    except FileNotFoundError:
        print(f'No file named "{filename}"')
        return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simple File Server Client')
    parser.add_argument('host', type=str, help='hostname to connect to')
    parser.add_argument('port', type=int, help='port to connect to')
    parser.add_argument('method', type=str,
                        help='method to perform [LIST, GET, PUT]')
    parser.add_argument('filename', type=str, nargs='?',
                        default='', help='filename for get and put method')

    args = parser.parse_args()

    HOST = args.host
    PORT = args.port

    if not args.method.upper() in {Method.PUT, Method.LIST, Method.GET}:
        print('Method Unknown: Only LIST, GET and PUT are supported')
        sys.exit(1)

    if args.method == Method.PUT:
        if not os.path.exists(args.filename):
            print(f'File file named "{args.filename}" exists. exiting...')
            sys.exit(1)

    addr = (HOST, PORT)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(addr)

        if args.method.upper() == Method.LIST:
            handle_list(s)
        elif args.method.upper() == Method.GET:
            handle_get(s, args.filename)
        elif args.method.upper() == Method.PUT:
            handle_put(s, args.filename)
