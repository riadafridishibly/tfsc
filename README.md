# Tiny File Server and Client
TFSC is an implementation of a simple file server and client on top of python's socket library. It uses the TCP protocol to communicate.

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
$ python client.py localhost 9009 PUT some-file
```


# Protocol Specification


| **2 bytes header size** | **header** | **content** |
|---|---|---|

The first 2 bytes of the request is fixed. It's ** 16-bit unsigned int** in *network byte* order (big-endian). It is the header size. Then the number of bytes specified by the first 2 bytes is the **header** length. In the header section, there's a field named *content-length* which specifies the data length after the header.

## Request Header
| Field | Description |
|---|---|
| content-length | Length of the data after the header |
| encoding | Encoding of the data. **UTF-8, binary**|
| method | Request type. **GET, PUT, LIST**|
| filename | File name specified in **GET** or **PUT** request |

## Response Header
| Field | Description |
|---|---|
| status | Status of the response **0 = OK, 1 = Error**|
| content-length | Length of the data after the header |
| encoding | Encoding of the data. **UTF-8, binary**|
| filename | File name specified in **GET** or **PUT** request |

## Methods
| Method | Description |
|---|---|
| GET | Download a file from the server |
| PUT | Upload a file to the server |
| LIST | List the contents of the directory in which the server is running |
