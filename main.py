#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import socket

s = socket.socket()         # Create a socket object
host = "10.0.0.16"
port = 12345                # Reserve a port for your service.

s.connect((host, port))
print (s.recv(1024))
s.close()                     # Close the socket when done
