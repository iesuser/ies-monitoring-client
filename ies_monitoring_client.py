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
# sent_messages list-ში ვინახავთ თითოეული გაგზავნილი მესიჯის დროს 
# დაგენერირებულ uuid-ს და მიმდინარე დროს
sent_messages = {}
# მესიჯის buffer_size
buffer_size = 8192

def string_to_datetime(date_time_str):
    return datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S.%f')

# ფუნქცია ქმნის სოკეტს და უკავშირდება ies_monitoring_server-ს
def connect_to_ies_monitoring_server():
    # შევქმნათ სოკეტი
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # დავუკავშირდეთ ies_monitoring_server-ს
    connection.connect((server_ip, server_port))
    return connection

def connection_close(connection):
    connection.shutdown(socket.SHUT_RDWR)
    connection.close()

# dictionary გადაყავს bytes ტიპში
def dictionary_to_bytes(dictionary_message):
    return bytes(json.dumps(dictionary_message), 'utf-8')

def wait_for_server_response(connection, message_id, resend_try_number, resend_delay, using_threading):
    # სანამ sent_messages არ არის ცარიელი
    # სანამ სერვერიდან ველოდებით შეტყობინებას მესიჯის მიღების დასტურად
    while True:
        time.sleep(0.2)
        received_message_bytes = connection.recv(buffer_size)
        received_message_id = received_message_bytes.decode("utf-8")
        if received_message_id == "":
            message_response_delay = datetime.datetime.now() - string_to_datetime(sent_messages[message_id]["sent_message_datetime"])
            print(message_response_delay)
            if message_response_delay > datetime.timedelta(seconds=resend_delay):
                print("wait_for_server_response|" , sent_messages[message_id]["sent_message_count"], "|")
                print(type(sent_messages[message_id]["sent_message_count"]))
                sent_message_count = sent_messages[message_id]["sent_message_count"] + 1
                if sent_message_count > resend_try_number:
                    connection_close(connection)
                    print("SMS გაგზავნა")
                    break
                connection_close(connection)
                print("resend count = ",sent_message_count)
                resend_message(sent_messages[message_id], resend_try_number, resend_delay, sent_message_count, using_threading)
                break
            continue
        if received_message_id in sent_messages:
            print(":::::::" + received_message_id)
            del sent_messages[received_message_id] 
            print("კავშირის დახურვა", datetime.datetime.now())
            connection.shutdown(socket.SHUT_RDWR)
            connection.close()
            break

# ფუნქციის საშუალებით ies_monitoring_server-ს შეგვიძლია გავუგზავნოთ შეტყობინება
def send_message_task(message_id, message_type, text, resend_try_number, resend_delay, sent_message_count, using_threading):
    print("send_message_task|" ,sent_message_count, "|")
    print("send_message_task=", type(sent_message_count))
    # დავუკავშირდეთ სერვერს
    connection = connect_to_ies_monitoring_server()

    if not message_id:
        # შეტყობინების უნიკალური id
        message_id = str(uuid.uuid4())
    # მესიჯის გაგზავნის დრო
    sent_message_datetime = str(datetime.datetime.now())
    # შევქმნათ message_data dictionary რასაც ვუგზავნით სერვერს
    message_data = {"message_id": message_id,
                    "message_type": message_type,
                    "text": text,
                    "sent_message_datetime": sent_message_datetime,
                    "sent_message_count" : sent_message_count}


    # sent_messages dictionary -ში ჩავამატოთ მიმდინარე მესიჯის უნიკალური Id-ი და დრო
    sent_messages[message_id] = message_data
    # გავაგზავნოთ შეტყობინება
    connection.send(dictionary_to_bytes(message_data))
    # გავწყვიტოთ კავშირი სერვერთან
    # connection.close()
    if using_threading:
        start_wait_for_server_response_thread(connection, message_id, resend_try_number, resend_delay)
    else:
        wait_for_server_response(connection, message_id, resend_try_number, resend_delay, False)

# thread-ის გამოყენებით შეტყობინების გაგზავნა.
def send_message_using_threading(message_id, message_type, text, resend_try_number, resend_delay, sent_message_count):
    print("send_message_using_threading|" ,sent_message_count, "|")
    print("send_message_using_threading=",type(sent_message_count))
    send_message_thread = threading.Thread(target = send_message_task, args = (message_id, message_type, text, resend_try_number, resend_delay, sent_message_count, True))
    send_message_thread.start()

def send_message(message_type, text, resend_try_number = 3, resend_delay = 3,  sent_message_count=1, using_threading=True, message_id = False):
    print("send_message|" ,sent_message_count, "|"," =")
    sent_message_count = int(sent_message_count)
    print("send_message=",type(sent_message_count))
    if using_threading:
        send_message_using_threading(message_id, message_type, text, resend_try_number, resend_delay, sent_message_count)
    else:
        send_message_task(message_id, message_type, text, resend_try_number, resend_delay, sent_message_count, using_threading=False)

def resend_message(message_data, resend_try_number, resend_delay, sent_message_count, using_threading):
    message_id = message_data["message_id"]
    message_type = message_data["message_type"]
    text = message_data["text"]
    print("resend_message|" ,sent_message_count, "|")
    print("resend_message=",type(sent_message_count))
    send_message(message_type, text, resend_try_number, resend_delay, sent_message_count, using_threading, message_id = False)

def start_wait_for_server_response_thread(connection, message_id, resend_try_number, resend_delay,):
    wait_for_server_response_thread = threading.Thread(target = wait_for_server_response, args = (connection, message_id, resend_try_number, resend_delay, True))
    wait_for_server_response_thread.start()

if __name__ == "__main__":
    send_message("blockkk", "ბ", using_threading=False)
    send_message("aaaa", "სერვერი დაიწვა", using_threading=False)
