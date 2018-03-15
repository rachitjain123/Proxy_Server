import base64,copy,thread,socket,sys,os,datetime,time,json,threading
import email.utils as eut
import itertools
import re

BUFFER_SIZE = 4096
CACHE_DIR = "./cache"
MAX_CACHE_BUFFER = 3
NO_OF_OCC_FOR_CACHE = 2

# take command line argument
proxy_port = 20000


def get_access(fileurl):
    if fileurl not in locks:
        lock = threading.Lock()
        locks[fileurl] = lock
    else:
        lock = locks[fileurl]
    lock.acquire()

def leave_access(fileurl):
    if fileurl in locks:
        lock = locks[fileurl]
        lock.release()


# add fileurl entry to log
def add_log(fileurl, client_addr):
    fileurl = fileurl.replace("/", "__")
    x=-1
    if fileurl in logs:
        x=1
    if x==-1:
        logs[fileurl] = []
    dt = time.strptime(time.ctime(), "%a %b %d %H:%M:%S %Y")
    logs[fileurl].append({
            "datetime" : dt,
            "client" : json.dumps(client_addr),
        })

# decide whether to cache or not
def do_cache_or_not(fileurl):
    log_arr = logs[fileurl.replace("/", "__")]
    last_third = log_arr[len(log_arr)-NO_OF_OCC_FOR_CACHE]["datetime"]
    if len(log_arr) < NO_OF_OCC_FOR_CACHE or datetime.datetime.fromtimestamp(time.mktime(last_third)) + datetime.timedelta(minutes=10) < datetime.datetime.now():
        return False
    return True

# check whether file is already cached or not
def get_current_cache_info(fileurl):

    if fileurl.startswith("/"):
        fileurl = fileurl.replace("/", "", 1)

    cache_path = CACHE_DIR + "/" + fileurl.replace("/", "__")

    if not os.path.isfile(cache_path):
        return cache_path, None
    else:
        last_mtime = time.strptime(time.ctime(os.path.getmtime(cache_path)), "%a %b %d %H:%M:%S %Y")
        return cache_path, last_mtime


def get_cache_details(client_addr, details):
    get_access(details["total_url"])
    add_log(details["total_url"], client_addr)
    cache_path, last_mtime = get_current_cache_info(details["total_url"])
    leave_access(details["total_url"])
    details["do_cache"] = do_cache_or_not(details["total_url"])
    details["cache_path"] = cache_path
    details["last_mtime"] = last_mtime
    return details


def get_space_for_cache(fileurl):
    cache_files = os.listdir(CACHE_DIR)
    if len(cache_files) >=MAX_CACHE_BUFFER:
        for file in cache_files:
            get_access(file)
        last_mtime = min(logs[file][-1]["datetime"] for file in cache_files)
        file_to_del = [file for file in cache_files if logs[file][-1]["datetime"] == last_mtime][0]

        os.remove(CACHE_DIR + "/" + file_to_del)
        for file in cache_files:
            leave_access(file)
    else:
        return



def parse_details(client_addr, client_data):
    lines = client_data.splitlines()
    for a in range(len(lines) - 1, -1, -1):
        if lines[a] == '':
            lines.remove('')
        else:
            break
    first_line = lines[0]
    first_line_split = first_line.split()
    url = first_line_split[1]
    client_split_data = re.split("://|:|/| ",client_data)
    first_line_split[1] = "/" + client_split_data[4]
    lines[0] = ' '.join(first_line_split)
    client_data = "\r\n".join(lines) + "\r\n\r\n"
    request_data = {
        "method": client_split_data[0],
        "protocol": client_split_data[1],
        "total_url": url,
        "server_port": int(client_split_data[3]),
        "server_url": client_split_data[2],
        "client_data": client_data
    }
    return request_data

def to_infinity():
    index=0
    while 1:
        yield index
        index += 1

# insert the header
def insert_if_modified(details):
    f1=0
    lines = details["client_data"].splitlines()
    for i in range(0,len(lines)):
        if lines[i]==' ':
            f1=-1
    f1=1
    if f1==1:
        while f1==1 and lines[len(lines)-1] == '':
            lines.remove('')
        stri = "If-Modified-Since: " + time.strftime("%a %b %d %H:%M:%S %Y", details["last_mtime"])
        lines.append(stri)
        details["client_data"] = "\r\n".join(lines) + "\r\n\r\n"
        return details


# serve get request
def get_request(client_socket, client_addr, details):
    url_file = details["total_url"]
    s_url=details["server_url"]
    s_port=details["server_port"]
    s_data=details["client_data"]
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.connect((s_url,s_port))
    server_socket.send(s_data)

    reply = server_socket.recv(BUFFER_SIZE)
    if details["last_mtime"] and "304 Not Modified" in reply:
        print "returning cached file %s" % (details["cache_path"])
        get_access(url_file)
        f = open(details["cache_path"], 'rb')
        chunk = f.read(BUFFER_SIZE)
        while chunk:
            client_socket.send(chunk)
            chunk = f.read(BUFFER_SIZE)
            if chunk<=0:
            	break
        f.close()
        leave_access(details["total_url"])

    elif details["do_cache"]:
        print "serving file and caching too ! %s " % (details["cache_path"])
        get_space_for_cache(details["total_url"])
        get_access(details["total_url"])
        f = open(details["cache_path"], "w+")
        while len(reply):
            client_socket.send(reply)
            f.write(reply)
            reply = server_socket.recv(BUFFER_SIZE)
            if reply<=0:
            	break
        f.close()
        leave_access(url_file)
        client_socket.send("\r\n\r\n")

    else:
        print "serving file without caching %s" % (details["cache_path"])
        while len(reply):
            client_socket.send(reply)
            reply = server_socket.recv(BUFFER_SIZE)
            if len(reply)<=0:
            	break
        client_socket.send("\r\n\r\n")

    server_socket.close()
    client_socket.close()
    return

# A thread function to handle one request
def request(client_socket, client_addr, client_data):

    details = parse_details(client_addr, client_data)
    if details:
        details = get_cache_details(client_addr, details)
        if details["last_mtime"]:
            details = insert_if_modified(details)
        get_request(client_socket, client_addr, details)
        client_socket.close()
        print client_addr, "closed"
    
    else:
        client_socket.close()
        return




def st_proxy():

    try:
        proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        proxy_socket.bind(('', proxy_port))
        proxy_socket.listen(10)


    except socket.gaierror:
        print "there was an error resolving the host"
        sys.exit()

    for i in itertools.count():
        client_socket, client_addr = proxy_socket.accept()
        client_data = client_socket.recv(BUFFER_SIZE)

        print "%s - -\"%s\"" % (str(client_addr),client_data.splitlines()[0])

        thread.start_new_thread(
            request,
            (
                client_socket,  
                client_addr,
                client_data
            )
        )

logs = {}
locks = {}
st_proxy()