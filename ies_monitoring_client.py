#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import socket
import json
import threading
import time
import datetime
import uuid

# ies_monitoring_server ის ip-ი მისამართი
server_ip = "10.0.0.16"
# ies_monitoring_server ის port-ი
server_port = 12345
# message_uuids list-ში ვინახავთ თითოეული გაგზავნილი მესიჯის დროს 
# დაგენერირებულ uuid-ს და მიმდინარე დროს
message_uuids = {}
# მესიჯის buffer_size
buffer_size = 8192

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

def wait_for_server_response(connection, message_id):
    print("=====================wait_for_server_response========================")
    # სანამ message_uuids არ არის ცარიელი
    # სანამ სერვერიდან ველოდებით შეტყობინებას მესიჯის მიღების დასტურად
    print(id(connection))
    # print(type(connection))
    while True:
        # print("++++++++++++++++++++++++++++++++++++++++++++++++++")
        # print(message_uuids)

        # print(connection)
        time.sleep(0.2)
        received_message_bytes = connection.recv(buffer_size)
        received_message_id = received_message_bytes.decode("utf-8")
        if received_message_id == "":
            print("მესიჯი არ მოსულა")
            print(datetime.datetime.now() - message_uuids[message_id])
            continue
        if received_message_id in message_uuids:
            print(":::::::" + received_message_id)
            print(message_uuids)
            del message_uuids[received_message_id]
            print("-----------")
            print(message_uuids)  
            print("კავშირის დახურვა", datetime.datetime.now())
            connection.shutdown(socket.SHUT_RDWR)
            connection.close()
            break
    print("იხურება: wait_for_server_response")

# ფუნქციის საშუალებით ies_monitoring_server-ს შეგვიძლია გავუგზავნოთ შეტყობინება
def send_message(message_type, text):
    # დავუკავშირდეთ სერვერს
    connect_to_ies_monitoring_server()

    # შეტყობინების უნიკალური id
    message_id = str(uuid.uuid4())
    # მესიჯის გაგზავნის დრო
    send_message_datetime = datetime.datetime.now()
    # message_uuids dictionary -ში ჩავამატოთ მიმდინარე მესიჯის უნიკალური Id-ი და დრო
    message_uuids[message_id] = send_message_datetime

    # შევქმნათ message_data dictionary რასაც ვუგზავნით სერვერს
    message_data = {"message_id": message_id, "message_type": message_type, "text": text}
    # გავაგზავნოთ შეტყობინება
    connection.send(dictionary_to_bytes(message_data))
    # გავწყვიტოთ კავშირი სერვერთან
    # connection.close()
    start_wait_for_server_response_thread(connection, message_id)
   

# thread-ის გამოყენებით შეტყობინების გაგზავნა.
def send_message_using_thread(message_type, text):
    send_message_thread = threading.Thread(target = send_message, args = (message_type, text))
    send_message_thread.start()

def start_wait_for_server_response_thread(connection, message_id):
    wait_for_server_response_thread = threading.Thread(target = wait_for_server_response, args = (connection, message_id))
    wait_for_server_response_thread.start()
    print("გაეშვა start_wait_for_server_response_thread")

if __name__ == "__main__":
    send_message("blockkk", "ბ")
    send_message("aaaa", "სერვერი დაიწვა")
