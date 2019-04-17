#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import socket
import json
import threading
import time

# ies_monitoring_server ის ip-ი მისამართი
server_ip = "10.0.0.16"
# ies_monitoring_server ის port-ი
server_port = 12345

# ფუნქცია ქმნის სოკეტს და უკავშირდება ies_monitoring_server-ს
def connect_to_ies_monitoring_server():
    # გლობალურად ავღწეროთ connection ცვლადი
    global connection
    # შევქმნათ სოკეტი
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # დავუკავშირდეთ ies_monitoring_server-ს
    connection.connect((server_ip, server_port))

# dictionary გადაყავს bytes ტიპში
def dictionary_to_bytes(dictionary_message):
    return bytes(json.dumps(dictionary_message), 'utf-8')

# ფუნქციის საშუალებით ies_monitoring_server-ს შეგვიძლია გავუგზავნოთ შეტყობინება
def send_message(message_type, text):
    connect_to_ies_monitoring_server()
    data = {"message_type": message_type, "text": text}
    time.sleep(3)
    connection.send(dictionary_to_bytes(data))
    print (connection.recv(1024))
    connection.close()

# thread-ის გამოყენებით შეტყობინების გაგზავნა.
def send_message_using_thread(message_type, text):
    send_message_thread = threading.Thread(target = send_message, args = (message_type, text))
    send_message_thread.start()

if __name__ == "__main__":
    send_message("ა", "ბ")
    send_message("aaaa", "სერვერი დაიწვა")
