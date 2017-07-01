#!/usr/bin/env python

import sys
import socket
import atexit
import base64
import threading
import select
import time
import Queue

import websocket # websocket-client on pypi

BUFFER_SIZE = 4096

def proxy(upstream_ws_url, listen_host='0.0.0.0', listen_port=0):

  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  s.bind((listen_host, listen_port))
  s.listen(1)

  def exit_handler():
    try:
      s.close()
    except Exception:
      pass
    try:
      ws.close()
    except Exception:
      pass
  atexit.register(exit_handler)

  def encode(data):
    return data if is_binary else base64.b64encode(data)
  def decode(data):
    return data if is_binary else base64.b64decode(data)

  def websocket_receiver(tcp, stop):
    try:
      while not stop.is_set():
        ready = select.select([ws], [], [], 1)
        if ready[0]:
          ws_data = ws.recv()
          if not ws_data: break
          tcp.send(decode(ws_data))
    except Exception as e:
      #print e
      stop.set()

  def tcp_receiver(stop):
    conn, addr = s.accept()
    print("tcp2ws: VNC Connection accepted: %s" % addr[0])
    print("tcp2ws: is_binary: %s" % is_binary)

    t2 = threading.Thread(target=websocket_receiver, args=(conn, stop))
    t2.start()

    try:
      while not stop.is_set():
        ready = select.select([conn], [], [], 1)
        if ready[0]:
          data = conn.recv(BUFFER_SIZE)
          if not data: break
          ws.send(encode(data))
    except Exception as e:
      #print e
      stop.set()

  ws = websocket.create_connection(upstream_ws_url, subprotocols=["binary", "base64"])
  is_binary = ws.getheaders().get('sec-websocket-protocol') == 'binary'

  stop = threading.Event()
  tcp_thread = threading.Thread(target=tcp_receiver, args=(stop,))
  tcp_thread.daemon = True
  tcp_thread.start()

  addr = s.getsockname()
  return ( addr[0], addr[1] )


if __name__ == "__main__":
  if len(sys.argv) == 4:
    listen_address = sys.argv[2]
    listen_port = int(sys.argv[3])
  elif len(sys.argv) == 2:
    listen_address = "127.0.0.1"
    listen_port = 0
  else:
    print("Usage: %s ws_url listen_address listen_port" % (sys.argv[0]))
    print("e.g. %s ws://3.5.2.1/path 127.0.0.1 3455" % (sys.argv[0]))
    exit(1)

  url = sys.argv[1]
  print( proxy(url, listen_address, listen_port) )
  while True:
    time.sleep(10)
