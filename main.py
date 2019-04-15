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
        self.buffer = 'GET %s HTTP/1.0\r\n\r\n' % path

    def handle_connect(self):
        pass

    def handle_close(self):
        self.close()

    def handle_read(self):
        print self.recv(8192)

    def writable(self):
        return (len(self.buffer) > 0)

    def handle_write(self):
        sent = self.send(self.buffer)
        self.buffer = self.buffer[sent:]


client = HTTPClient(host, port)
asyncore.loop()