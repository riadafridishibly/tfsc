# Tiny File Server and Client
TFSC is a implementation of simple file server and client on top of python's socket library. It uses TCP protocol to communicate.

# Usage
Run the `server.py` and `client.py` in two different folders to avoid filename conflict.

## Running the server
```
$ python server.py <port>
```
Example:
```
$ python server.py 9009
```

## Using the client
```
$ python client.py <host> <port> <request-type> <filename | only for GET and PUT request>
```
Example:
```
$ python client.py localhost 9009 GET README.md
$ python client.py localhost 9009 LIST
$ python client.py localhost 9009 PUT somefile
```


# Protocol Specification


| **2 bytes header size** | **header** | **content** |
|---|---|---|

The first 2 bytes of the request is fixed. It's **16 bit unsigned int** in *network byte* order (big endian). It is the header size. Then the number of bytes specified by the first 2 bytes is the **header** length. In the header section there's a field named *content-length* which specifies the data length after the header.

## Request Header
| Field | Description |
|---|---|
| content-length | Length of the data after the header |
| encoding | Encoding of the data. **utf-8, binary**|
| method | Request type. **GET, PUT, LIST**|
| filename | File name specified in **GET** or **PUT** request |

## Response Header
| Field | Description |
|---|---|
| status | Status of the response **0 = OK, 1 = Error**|
| content-length | Length of the data after the header |
| encoding | Encoding of the data. **utf-8, binary**|
| filename | File name specified in **GET** or **PUT** request |
