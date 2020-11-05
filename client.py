#!/usr/bin/env python

import socket
import struct
import sys
import json
import argparse
import os


class Status:
    OK = 0
    ERROR = 1


class Method:
    LIST = 'LIST'
    GET = 'GET'
    PUT = 'PUT'


# Generate HEADER for each request
def generate_header(
        content_length: int,
        method: str,
        filename: str = '',
        encoding: str = 'utf-8') -> bytes:
    header = {}
    header['content-length'] = content_length
    header['encoding'] = encoding
    header['method'] = method
    if method != 'list':
        header['filename'] = filename
    dumped_header = json.dumps(header).encode('utf-8')
    return struct.pack('>H', len(dumped_header)) + dumped_header


# Read from socket and returns byte
def read_from_socket(sock: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            break
        data.extend(packet)
    return bytes(data)

# Read header returned from server


def read_header(sock) -> dict:
    raw_size = sock.recv(2)
    if not raw_size:
        print('Read failed from', addr)
    size = struct.unpack('>H', raw_size)[0]
    data = read_from_socket(sock, size)
    return json.loads(data)


# Handle the list command


def handle_list(sock):
    header = generate_header(content_length=0, method='LIST')
    sock.sendall(header)

    received_header = read_header(sock)
    content_len = received_header.get('content-length')

    data = read_from_socket(sock, content_len)
    print(data.decode(received_header.get('encoding')))

# Handle the get command


def handle_get(sock, filename):
    header = generate_header(
        content_length=0, method='GET', filename=filename, encoding='binary')
    sock.sendall(header)

    received_header = read_header(sock)
    status = received_header.get('status')
    content_len = received_header.get('content-length')

    # print(received_header)
    if status != 0:
        data = read_from_socket(sock, content_len).decode(
            received_header.get('encoding'))
        print(data, file=sys.stderr)
        return None

    filename = received_header.get('filename')

    # if os.path.isfile(filename):
    #     print('File Exists:', filename)
    #     return None

    n = 0
    with open(filename, 'wb') as f:
        while n < content_len:
            data = sock.recv(4096)
            if not data:
                break
            n += f.write(data)

# Handle the put command


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

