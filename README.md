# Proxy Server
 An HTTP proxy server implemented via python socket programming
with caching
## Description
- ![proxy.py](/proxy.py ) is the main proxy file
- Proxy runs on port 20000
- Proxy works as middleman between the server and client and it does caching, authentication, etc
- GET request is only handled.

## Features
- Receives the request from client and pass it to the server after necessary parsing
- Threaded proxy server thus able to handle many requests at the same time
- If one file is requested above the threshold number of times in certain time period, then proxy server caches that request.
- To maintain integrity, cached files are accessed by securing mutex locks
- Cache has limited size, so if the cache is full and proxy wants to store another response then it removes the least recently asked cached response. Cache limit can be set by setting up the constant in ![proxy.py](/proxy.py ) file

## How to run
   
### Proxy
- Specify proxy port while running proxy
`python proxy.py `

### Server
- run server in ![server](/server ) directory
- python server.py to run server on port 19999

### Client
- start the server first by going into the server directory and
type the command python "server.py".
- start the proxyserver by going into the proxyserver directory
and type the command python "proxyserver.py".
- the proxyserver now acts as a proxy to all the network actions
requesting the proxy through the port 12345
- curl request can be sent as client request and get the
response.
 `curl --request GET --proxy 127.0.0.1:20000 --local-port
20001-20010 127.0.0.1:19999/<"filename">`
- this request will ask 1.data file from server 127.0.0.1/19999
by GET request via proxy 127.0.0.1/20000 using one of the ports
in range 20001-20010 on localhost.
- if the file already exists in the cache of proxy server and is
not changed in the server then it is directly served to the
client     by the proxy itself i.e the server is not requested
for the file. If the file was updated in the server then the
updated file is      downloaded and stored in the cache of proxy
server
- If the file already doesn't exist in the cache of proxy server
then it is downloaded from the server by
 a HTTP request and then it is served to the client.
