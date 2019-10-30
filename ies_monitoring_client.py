#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import socket
import threading
import time
import datetime
import uuid
import logging
import pickle

"""
    1. print("SMS გაგზავნა") ჩასმულია ქვემოთ სადაც უნდა გაიგზავნოს SMS-ი
    2. send_message ფუნქციას ქონდეს მეილზეც გაგზავნის საშუალება ან იყოს ცალკე ფუნქციად
"""

# ies_monitoring_server ის ip-ი მისამართი
server_ip = "10.0.0.194"

# ies_monitoring_server ის port-ი
server_port = 12345

# sent_messages list-ში ვინახავთ თითოეული გაგზავნილი მესიჯის დროს
# დაგენერირებულ uuid-ს და მიმდინარე დროს
sent_messages = {}

# მესიჯის buffer_size
buffer_size = 8192

# მესიჯის ჰედერის სიგრძე
HEADERSIZE = 10

# log ფაილის დასახელება
log_filename = "log"

# logger შექმნა
logger = logging.getLogger('ies_monitoring_client_logger')
logger.setLevel(logging.DEBUG)

# FileHandler - ის შექმნა. დონის და ფორმატის განსაზღვრა
log_file_handler = logging.FileHandler(log_filename)
log_file_handler.setLevel(logging.DEBUG)
log_file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
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

    # დავუკავშირდეთ ies_monitoring_server-ს და დავაბრუნოთ connection ობიექტი
    try:
        connection.connect((server_ip, server_port))
        logger.debug("სერვერთან დამყარდა კავშირი: " + str(connection.getpeername()))
        return connection
    except Exception as ex:
        logger.error("სერვერთან კავშირი ვერ დამყარდა. Exception: " + str(ex))
        return False


def connection_close(connection):
    """ხურავს (კავშირს სერვერთან) პარამეტრად გადაცემულ connection socket ობიექტს"""

    logger.debug("სერვერთან კავშირის დახურვა: " + str(connection.getpeername()))
    connection.shutdown(socket.SHUT_RDWR)
    connection.close()


def dictionary_message_to_bytes(message):
    """ ფუნქციას dictionary ტიპის მესიჯი გადაყავს bytes ტიპში და თავში უმატებს header-ს """

    # dictionary გადადის bytes ტიპში (serialization)
    message_bytes = pickle.dumps(message)

    # მესიჯის სიგრძე დათვლა
    message_length = len(message_bytes)

    # header-ი გადავიყვანოთ ბაიტებში და დავუმატოთ გადაყვანილი მესიჯი byte-ებში
    message_bytes = bytes(str(message_length).ljust(HEADERSIZE), 'utf-8') + message_bytes

    # ფუნქცია აბრუნებს მესიჯს გადაყვანილს ბაიტებში თავისი header-ით
    return message_bytes


def wait_for_server_response(connection, message_id, resend_try_number, resend_delay, using_threading):
    """ყოველი გაგზავნილი შეტყობინებისთვის ეშვება wait_for_server_response ფუნქცია რომელიც
    ელოდება სერვერისგან პასუხს იმის დასტურად რომ სერვერმა მიიღო შეტყობინება.
    იმ შემთხვევაში თუ სერვერიდან პასუხი არ მოვიდა ფუნქცია თავდიდან ცდილობს გააგზავნოს
    შეტყობინება."""

    while True:
        # წიკლის შეჩერება 0.2 წამით
        time.sleep(0.2)

        # შევამოწმოთ თუ სერვერთან გვაქვს კავშირი
        if connection is not False:
            # წავიკითხოთ connection ობიექტზე მიღებუი ინფორმაცია
            # წაკითხვა ხდება bytes ტიპში (connection.recv აბრუნებს bytes ობიექტს)
            received_message_bytes = connection.recv(buffer_size)

            # bytes გადავიყვანოთ string ტიპში
            received_message_id = received_message_bytes.decode("utf-8")
        else:
            received_message_id = ""

        # შევამოწმოთ თუ სერვერისგან მივიღეთ შეტყობინება
        if received_message_id == "":

            # დავთვალოთ რა დრო გავიდა გაგზავნილი შეტყობინების მერე
            message_response_delay = datetime.datetime.now(
            ) - string_to_datetime(sent_messages[message_id]["sent_message_datetime"])

            # შევამოწმოთ გაგზავნილი შეტყობინების მერე თუ გავიდა resend_delay
            # წუთზე მეტი
            if message_response_delay > datetime.timedelta(seconds=resend_delay):
                # დავთვალოთ მერამდენედ ვაგზავნით ამ კონკრეტულ შეტყობინებას
                sent_message_count = sent_messages[message_id]["sent_message_count"] + 1

                # თუ შეტყობინების გაგზავნა მოხდა resend_try_number ჯერ
                # შევწყვიტოთ ხელახლა გაგზავნა
                if sent_message_count > resend_try_number:
                    # შევამოწმოთ თუ სერვერთან გვაქვს კავშირი
                    if connection is not False:
                        # კავშირის დახურვა
                        connection_close(connection)

                    # წავშალოთ ინფორმაცია (dictionary) გაგზავნილ შეტყობინებაზე
                    # sent_messages-დან
                    del sent_messages[message_id]

                    print("SMS გაგზავნა")

                    # სერვერიდან აღარ ველოდებით პასუხს, აღარ ვაგზავნით დავიდან
                    # და გამოვდივართ ციკლიდან
                    break

                # შევამოწმოთ თუ სერვერთან გვაქვს კავშირი
                if connection is not False:
                    # კავშირის დახურვა
                    connection_close(connection)
                    logger.error("სერვერთან კავშირი დამყარდა, მაგრამ არ მოსულა შეტყობინების"
                                 " მიღების დასტური: " + sent_messages[message_id]["message_id"])
                else:
                    logger.error("სერვერთან კავშირი ვერ დამყარდა. message_id: {" +
                                 sent_messages[message_id]["message_id"] + "}")

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
            logger.debug("სერვერმა გამოაგზავნა შეტყობინების მიღების დასტური. message_id: {" + received_message_id + "}")

            # წავშალოთ ინფორმაცია (dictionary) გაგზავნილ შეტყობინებაზე
            # sent_messages-დან
            del sent_messages[received_message_id]

            # კავშირის დახურვა
            connection_close(connection)

            # ციკლიდან გამოსვლა
            break


def send_message_task(message_id, message_type, message_title, text, resend_try_number,
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
        "message_title": message_title,
        "text": text,
        "sent_message_datetime": sent_message_datetime,
        "sent_message_count": sent_message_count,
        "client_script_name": sys.argv[0].strip("./"),
        "who_am_i": "ies_monitoring_client"
    }

    # შევამოწმოთ თუ სერვერთან გვაქვს კავშირი
    if connection is not False:
        message_data["client_ip"] = connection.getsockname()[0]

        # გავაგზავნოთ შეტყობინება
        try:
            connection.send(dictionary_message_to_bytes(message_data))
            logger.debug("სერვერზე გაიგზავნა შემდეგი შეტყობინება: " + str(message_data))
        except Exception as ex:
            logger.error("სერვერზე ვერ გაიგზავნა შემდეგი შეტყობინება: " + str(message_data) + "\n" + str(ex))

    # sent_messages dictionary -ში ჩავამატოთ მიმდინარე მესიჯის უნიკალური Id-ი და დრო
    sent_messages[message_id] = message_data

    # ვიყენებთ თუ არა threading-ს
    if using_threading:
        # wait_for_server_response გავუშვათ ცალკე thread-ში start_wait_for_server_response_thread ფუნქციის გამოძახებით
        start_wait_for_server_response_thread(
            connection, message_id, resend_try_number, resend_delay)
    else:
        # გავუშვათ wait_for_server_response ფუნქცია Thread-ის გარეშე
        wait_for_server_response(
            connection, message_id, resend_try_number, resend_delay, False)


def send_message_using_threading(message_id, message_type, message_title, text, resend_try_number, resend_delay, sent_message_count):
    """ thread-ის გამოყენებით შეტყობინების გაგზავნა. """

    # შევქმნათ thred-ი send_message_task ფუნქციის საშუალებით
    send_message_thread = threading.Thread(target=send_message_task, args=(
        message_id, message_type, message_title, text, resend_try_number, resend_delay, sent_message_count, True))

    # გავუშვათ send_message_thread-ი
    send_message_thread.start()


def send_message(message_type, message_title, text, resend_try_number=3, resend_delay=3,
                 sent_message_count=1, using_threading=True, message_id=False):
    """
    ფუნქციის საშუალებით შეგვიძლია ies_monitoring_server-ს გავუგზავნოთ შეტყობინება
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
        send_message_using_threading(message_id, message_type, message_title, text, resend_try_number,
                                     resend_delay, sent_message_count)
    else:
        # გავუშვათ send_message_task ფუნქცია Thread-ის გარეშე
        send_message_task(message_id, message_type, message_title, text, resend_try_number,
                          resend_delay, sent_message_count, using_threading=False)


def resend_message(message_data, resend_try_number, resend_delay, sent_message_count, using_threading):
    """ ფუნქციას ვიყენბთ იმ შემთხვევაში როდესაც სერვერიდან პასუხი არ მოდის და ვაგზავნით თავიდან """

    # წავიკითხოთ message_id-ი message_data dictionary-დან
    message_id = message_data["message_id"]

    # წავიკითხოთ message_type-ი message_data dictionary-დან
    message_type = message_data["message_type"]

    # წავიკითხოთ message_title-ი message_data dictionary-დან
    message_title = message_data["message_title"]

    # წავიკითხოთ text-ი message_data dictionary-დან
    text = message_data["text"]

    logger.debug("შეტყობინება {" + message_id + "} იგზავნება ხელახლა მე " + str(sent_message_count) + " - ჯერ")
    # შეტყობინების გაგზავნა
    send_message(message_type, message_title, text, resend_try_number, resend_delay,
                 sent_message_count, using_threading, message_id=message_id)


def start_wait_for_server_response_thread(connection, message_id, resend_try_number, resend_delay):
    """ thread -ის გამოყენებით wait_for_server_response_thread ფუნქციის გაშვება """

    # შევქმნათ thred-ი wait_for_server_response ფუნქციის საშუალებით
    wait_for_server_response_thread = threading.Thread(target=wait_for_server_response, args=(
        connection, message_id, resend_try_number, resend_delay, True))

    # გავუშვათ wait_for_server_response_thread-ი
    wait_for_server_response_thread.start()


if __name__ == "__main__":
    # send_message("block", "ბ", using_threading=True)
    # send_message("aaaa", "სერვერი დაიწვა", using_threading=True)
    i = 1
    while i <= 1:
        time.sleep(0.01)
        send_message("block", "სერვერზე მოხდა დროის არევა", "სერვერზე მოხდა დროის არევა "
                     "ან არქივში ვერ მოიძებნა წინა დღის არქივი სერვერის დრო : 2019-04-02 02:00:04 "
                     "ელფოსტა გამოიგზავნა iesresource-ის დაარქივებისას", resend_delay=1, using_threading=False)
        i += 1
