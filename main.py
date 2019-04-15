#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import socket
import asyncore

host = "10.0.0.16"
port = 12345                # Reserve a port for your service.

# s = socket.socket()         # Create a socket object
# host = "10.0.0.16"
# port = 12345                # Reserve a port for your service.

# s.connect((host, port))
# print (s.recv(1024))
# s.close()                     # Close the socket when done

class HTTPClient(asyncore.dispatcher):

    def __init__(self, host, port):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))
        self.buffer = "test message"

    def handle_connect(self):
        print("handle_connect")
        pass

    def handle_close(self):
        print("handle_close")
        self.close()

    def handle_read(self):
        print("handle_read")
        print(self.recv(8192))

    def writable(self):
        print("writable")
        return (len(self.buffer) > 0)

    def handle_write(self):
        print("handle_write")
        sent = self.send(self.buffer)
        self.buffer = self.buffer[sent:]


client = HTTPClient(host, port)
asyncore.loop()