#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import socket
import json
import threading
import time
import datetime
import uuid
import logging

# ies_monitoring_server ის ip-ი მისამართი
server_ip = "10.0.0.20"

# ies_monitoring_server ის port-ი
server_port = 12345

# sent_messages list-ში ვინახავთ თითოეული გაგზავნილი მესიჯის დროს
# დაგენერირებულ uuid-ს და მიმდინარე დროს
sent_messages = {}

# მესიჯის buffer_size
buffer_size = 8192

# log ფაილის დასახელება
log_filename = "imc_log"

# logger შექმნა
logger = logging.getLogger('ies_monitoring_client_logger')
logger.setLevel(logging.DEBUG)

# FileHandler - ის შექმნა. დონის და ფორმატის განსაზღვრა
log_file_handler = logging.FileHandler(log_filename)
log_file_handler.setLevel(logging.DEBUG)
log_file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s \n")
log_file_handler.setFormatter(log_file_formatter)
logger.addHandler(log_file_handler)


def string_to_datetime(date_time_str):
    """ string ტიპის დრო გადაყავს datetime ტიპში """

    # დრო date_time_str string-ი გადავიყვანოთ datetime ობიექტში და დავაბრუნოთ ფუუნქციის მნიშვნლობა
    return datetime.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S.%f')


def connect_to_ies_monitoring_server():
    """ფუნქცია ქმნის სოკეტს და უკავშირდება ies_monitoring_server-ს """

    # შევქმნათ სოკეტი
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # დავუკავშირდეთ ies_monitoring_server-ს
    connection.connect((server_ip, server_port))

    # დავაბრუნოთ connection ობიექტი
    return connection


def connection_close(connection):
    """ხურავს (კავშირს სერვერთან) პარამეტრად გადაცემულ connection socket ობიექტს"""

    connection.shutdown(socket.SHUT_RDWR)
    connection.close()


def dictionary_to_bytes(dictionary_message):
    """
    dictionary ტიპის ობიექტი გადაყავს bytes ტიპში
    რადგან socket ობიექტის გამოყენებით მონაცემები იგზავნება bytes ტიპში
    მოსახერხებელია რომ გვქონდეს ფუნქციები რომელიც dictionary-ის გადაიყვანს
    bytes ტიპში და პირიქით
    """

    return bytes(json.dumps(dictionary_message), 'utf-8')


def wait_for_server_response(connection, message_id, resend_try_number, resend_delay, using_threading):
    """ყოველი გაგზავნილი შეტყობინებისთვის ეშვება wait_for_server_response ფუნქცია რომელიც
    ელოდება სერვერისგან პასუხს იმის დასტურად რომ სერვერმა მიიღო შეტყობინება
    იმ შემთხვევაში თუ სერვერიდან პასუხი არ მოვიდა ფუნქცია თავდიდან ცდილობს გააგზავნოს
    შეტყობინება."""

    while True:
        # წიკლის შეჩერება 0.2 წამით
        time.sleep(0.2)

        # წავიკითხოთ connection ობიექტზე მიღებუი ინფორმაცია
        # წაკითხვა ხდება bytes ტიპში (connection.recv აბრუნებს bytes ობიექტს)
        received_message_bytes = connection.recv(buffer_size)

        # bytes გადავიყვანოთ string ტიპში
        received_message_id = received_message_bytes.decode("utf-8")

        # შევამოწმოთ თუ სერვერისგან მივიღეთ შეტყობინება
        if received_message_id == "":

            # დავთვალოთ რა დრო გავიდა გაგზავნილი შეტყობინების მერე
            message_response_delay = datetime.datetime.now(
            ) - string_to_datetime(sent_messages[message_id]["sent_message_datetime"])

            # შევამოწმოთ გაგზავნილი შეტყობინების მერე თუ გავიდა resend_delay
            # წუთზე მეტი
            if message_response_delay > datetime.timedelta(seconds=resend_delay):
                # დავთვალოთ მერამდენედ ვაგზავნით ამ კონკრეტულ შეტყობინებას
                sent_message_count = sent_messages[
                    message_id]["sent_message_count"] + 1

                # თუ შეტყობინების გაგზავნა მოხდა resend_try_number ჯერ
                # შევწყვიტოთ ხელახლა გაგზავნა
                if sent_message_count > resend_try_number:
                    # კავშირის დახურვა
                    connection_close(connection)

                    # წავშალოთ ინფორმაცია (dictionary) გაგზავნილ შეტყობინებაზე
                    # sent_messages-დან
                    del sent_messages[message_id]

                    print("SMS გაგზავნა")

                    # სერვერიდან აღარ ველოდებით პასუხს, აღარ ვაგზავნით დავიდან
                    # და გამოვდივართ ციკლიდან
                    break

                # კავშირის დახურვა
                connection_close(connection)

                # წასაშლელია
                print("resend count = ", sent_message_count)

                # ხელახლა გავაგზავნოთ შეტყობინება
                resend_message(sent_messages[message_id], resend_try_number,
                               resend_delay, sent_message_count, using_threading)
                # ციკლიდან გამოსვლა
                break

            # თუ სერვერიდან მიღებული ბაიტები არის ცარიელი წავიკითხოთ თავიდან
            # გამოვტოვოთ ციკლის ერთი ბიჯი
            continue

        # თუ სერვერიდან მივიღეთ გაგზავნილი შეტყობინების message_id ესეიგი
        # სერვერმა მიიღო შეტყობინება
        if received_message_id in sent_messages:
            print(":::::::" + received_message_id)

            # წავშალოთ ინფორმაცია (dictionary) გაგზავნილ შეტყობინებაზე
            # sent_messages-დან
            del sent_messages[received_message_id]

            # კავშირის დახურვა
            connection_close(connection)

            # ციკლიდან გამოსვლა
            break


def send_message_task(message_id, message_type, text, resend_try_number,
                      resend_delay, sent_message_count, using_threading):
    """ ფუნქციას იყენებს send_message ფუნქცია და მისი საშუალებით
        ies_monitoring_server-ს შეგვიძლია გავუგზავნოთ შეტყობინება """

    # დავუკავშირდეთ სერვერს
    connection = connect_to_ies_monitoring_server()

    # შევამოწმოთ თუ message_id არის ცარიელი
    if not message_id:
        # თუ message_id არის ცარიელი დავაგენერიროთ ახალი Id
        message_id = str(uuid.uuid4())

    # მესიჯის გაგზავნის დრო
    sent_message_datetime = str(datetime.datetime.now())

    # შევქმნათ message_data dictionary რასაც ვუგზავნით სერვერს
    message_data = {
        "message_id": message_id,
        "message_type": message_type,
        "text": text,
        "sent_message_datetime": sent_message_datetime,
        "sent_message_count": sent_message_count,
        "client_ip": connection.getsockname()[0],
        "client_script_name": sys.argv[0].strip("./")
    }

    # sent_messages dictionary -ში ჩავამატოთ მიმდინარე მესიჯის უნიკალური Id-ი და დრო
    sent_messages[message_id] = message_data

    # გავაგზავნოთ შეტყობინება
    connection.send(dictionary_to_bytes(message_data))

    # ვიყენებთ თუ არა threading-ს
    if using_threading:
        # wait_for_server_response გავუშვათ ცალკე thread-ში start_wait_for_server_response_thread ფუნქციის გამოძახებით
        start_wait_for_server_response_thread(
            connection, message_id, resend_try_number, resend_delay)
    else:
        # გავუშვათ wait_for_server_response ფუნქცია Thread-ის გარეშე
        wait_for_server_response(
            connection, message_id, resend_try_number, resend_delay, False)


def send_message_using_threading(message_id, message_type, text, resend_try_number, resend_delay, sent_message_count):
    """ thread-ის გამოყენებით შეტყობინების გაგზავნა. """

    # შევქმნათ thred-ი send_message_task ფუნქციის საშუალებით
    send_message_thread = threading.Thread(target=send_message_task, args=(
        message_id, message_type, text, resend_try_number, resend_delay, sent_message_count, True))

    # გავუშვათ send_message_thread-ი
    send_message_thread.start()


def send_message(message_type, text, resend_try_number=3, resend_delay=3,
                 sent_message_count=1, using_threading=True, message_id=False):
    """
    უნქციის საშუალებით შეგვიძლია ies_monitoring_server-ს გავუგზავნოთ შეტყობინება
    პარამეტრები:
    message_type - მესიჯის ტიპი
    text - შეტყობინების ტექსტი
    resend_try_number - იმ შემთხვევაში თუ სერვერმა ვერ მიიღო შეტყობინება რამდენჯერ ცადოს ხელახლა გაგზავნა
    resend_delay - იმ შემთხვევაში თუ სერვერმა ვერ მიიღო შეტყობინება რამდენი წუთის მერე ცადოს ხელახლა გაგზავნა
    using_threading - ფუნქცია გაეშვას ცალკე Thread-ით თუ არა. თუ გვინდა რომ ფუნქცია გაეშვას thread-ის გარეშე
                      მივუთითოთ using_threading=False. using_threading პარამეტრის default მნიშვნელობა არის True
    """

    # ვიყენებთ თუ არა threading-ს
    if using_threading:
        # send_message_task გავუშვათ ცალკე thread-ში send_message_using_threading ფუნქციის გამოძახებით
        send_message_using_threading(message_id, message_type, text, resend_try_number,
                                     resend_delay, sent_message_count)
    else:
        # გავუშვათ send_message_task ფუნქცია Thread-ის გარეშე
        send_message_task(message_id, message_type, text, resend_try_number,
                          resend_delay, sent_message_count, using_threading=False)


def resend_message(message_data, resend_try_number, resend_delay, sent_message_count, using_threading):
    """ ფუნქციას ვიყენბთ იმ შემთხვევაში როდესაც სერვერიდან პასუხი არ მოდის და ვაგზავნით თავიდან """

    # წავიკითხოთ message_id-ი message_data dictionary-დან
    message_id = message_data["message_id"]

    # წავიკითხოთ message_type-ი message_data dictionary-დან
    message_type = message_data["message_type"]

    # წავიკითხოთ text-ი message_data dictionary-დან
    text = message_data["text"]

    # შეტყობინების გაგზავნა
    send_message(message_type, text, resend_try_number, resend_delay,
                 sent_message_count, using_threading, message_id=message_id)


def start_wait_for_server_response_thread(connection, message_id, resend_try_number, resend_delay):
    """ thread -ის გამოყენებით wait_for_server_response_thread ფუნქციის გაშვება """

    # შევქმნათ thred-ი wait_for_server_response ფუნქციის საშუალებით
    wait_for_server_response_thread = threading.Thread(target=wait_for_server_response, args=(
        connection, message_id, resend_try_number, resend_delay, True))

    # გავუშვათ wait_for_server_response_thread-ი
    wait_for_server_response_thread.start()


if __name__ == "__main__":
    # send_message("blockkk", "ბ", using_threading=True)
    # send_message("aaaa", "სერვერი დაიწვა", using_threading=True)
    i = 1
    while i <= 10:
        time.sleep(0.01)
        send_message("aaaa", "სერვერი დაიწვა", using_threading=True)
        i += 1
