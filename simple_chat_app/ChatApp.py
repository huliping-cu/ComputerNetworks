
import time
import queue
from socket import *
import os
import sys
import ipaddress
import threading
import select
from datetime import datetime



class Client:
    def __init__(self, ip, port, nickName, status):
        self.ip = ip
        self.port = port
        self.nickName = nickName
        self.status = status

def runServer():
    serverTable = dict()
    saved_msg = dict()
    channel = dict()
    ack_container = set()
    received_requests = queue.Queue()
    off_client = None

    threading.Thread(target=listen,args=(ack_container,received_requests,)).start()

    while True:
        while not received_requests.empty():
            message, clientAddress = received_requests.get()

            # When receives a client REGISTRATION request
            if message[0] == "REGISTRATION":
                name = message[1]
                if name not in serverTable.keys():
                    serverTable = update_table(name, serverTable,clientAddress,channel)
                else:
                    sendtoString = ("duplicated " + "Nick name already exist, please choose a different one").encode()
                    serverSocket.sendto(sendtoString, clientAddress)

            # When receives a client register back request
            elif message[0] == "reg":
                name = message[1]
                update_table_online(name, serverTable, serverSocket,channel,saved_msg)

            # When receives a client de-register request
            elif message[0] == "dereg":
                name = message[1]
                send_dereg_ack(name, serverTable)
                update_table_offline(name, serverTable,channel)

            # When receives a client's save message request (receiver is offline)
            elif message[0] == "save_msg":
                # save message and display to receiver later
                sender = message[1]
                receiver = message[2]
                timeee = ' '.join(message[3:8])
                timeee = timeee.split(",")
                timeee = " ".join(timeee)
                msg = message[8:]
                msg = " ".join(msg)
                msgg = msg
                msg = sender + ":" + ' ' + timeee + ' ' + msg
                # Put client in saved_msg dictionary if not there yet

                if receiver not in saved_msg:
                    saved_msg[receiver] = []

                if message[-1] != "retry":
                    # when duplicated user exists
                    if serverTable[receiver].status == "active":
                        sendto_msg = ("[Client" + receiver + "exists!!]").encode()
                        serverSocket.sendto(sendto_msg, clientAddress)
                    # append the message-to-be-saved in to dictionary under correct client
                    # only if the message is not duplicated message from retrying

                    # if time not in saved_msg[receiver]:
                    if msg not in saved_msg[receiver]:
                        saved_msg[receiver].append(msg)
                        if sender != receiver:
                            serverSocket.sendto("savedmsg_ack [Messages received by the server and saved. ]".encode(),
                                                clientAddress)
                else:
                    if msg[:len(msg)-6] not in saved_msg[receiver]:
                        saved_msg[receiver].append(msg[:len(msg)-6])
                        if sender != receiver:
                            serverSocket.sendto("savedmsg_ack [Messages received by the server and saved. ]".encode(),
                                                clientAddress)
                    serverSocket.sendto("savedmsg_ack".encode(), clientAddress)

            elif message[0] == "send_all":
                if message[-1] != "retry":

                    # SEND THE MESSAGE TO CLIENTS IN THE CHANNEL
                    active_clients = {}
                    inactive_clients = {}
                    unresponded_clients = {}

                    sender = message[-1]
                    msg = message[1:len(message) - 1]

                    # serverSocket.sendto("ACK_GROUP".encode(), clientAddress)

                    for person, client in serverTable.items():
                        # update active_clients and inactive_clients dictionary
                        if client.status == "active":
                            active_clients[person] = client
                            unresponded_clients[person] = client
                        else:
                            inactive_clients[person] = client

                    msg = ' '.join(msg)
                    t = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                    t = t.split(",")
                    t = " ".join(t)

                    save = "Channel_Message " + sender + ":" + " " + t + " " + msg

                    # save the message for inactive clients to be displayed later when they reg back
                    for person in inactive_clients:

                        if person not in saved_msg:
                            saved_msg[person] = []
                        print("saved_msg[person]", saved_msg[person])
                        if msg not in saved_msg[person]:
                            saved_msg[person].append(save)
                    print("saved_msg",saved_msg)

                    for x in saved_msg:
                        print("item in saved_msg: ", x)
                    # send the channel message for active clients
                    for person in active_clients:
                        if person != sender:
                            sendto_msg = "Channel_Message " + sender + ":" + " " + msg + " " + person
                            sendto_addr = (serverTable[person].ip, serverTable[person].port)
                            serverSocket.sendto(sendto_msg.encode(), sendto_addr)
                    # sleep for 500 milliseconds and check if all clients has sent ack to check for
                    # clients who has silent left (closing their ssh window)
                    time.sleep(0.5)
                    # print("\n","after timeout, unresponded_clients: ",unresponded_clients.keys(),"ack_container is: ",ack_container,"active_clients is: ",active_clients.keys())
                    active_clients.pop(sender)
                    # print("after pop, ack_container is: ",ack_container,"active_clients is: ",active_clients.keys())

                    # when found a silent-left client
                    for user in active_clients:
                        if user not in ack_container:
                            # print("off_client user: ", user)
                            off_client = user
                            update_table_offline(off_client, serverTable,channel)

                    # when there is a client who didn't leave the chat correctly, broadcast to other
                    # clients about the change
                    if off_client is not None:
                        for name, client in serverTable.items():
                            # print(name, "is ", client.status)
                            # broadcast to active clients
                            if client.status == "active":
                                broadcast(name, serverTable, serverTable[name])
                else:


                    # serverSocket.sendto("savedmsg_ack [Messages received by server. ]".encode(),
                    #                         clientAddress)
                    # serverSocket.sendto("savedmsg_ack".encode(), clientAddress)
                    serverSocket.sendto("ACK_GROUP".encode(), clientAddress)

                ack_container.clear()

    serverSocket.close()
    sys.exit(1)
def validate_input(args, serverPort):
    if len(args) != 3:
        print("Usage: ChatApp.py -s <port>")
        return False
    elif serverPort < 1024 or serverPort > 65535:
        print("correct server port number range: [1024,65535]")
        return False
    return True
def listen(ack_container,received_requests):
    """
    listening to received messages from either clients or server, and put the messages in
    a queue to deal with later according to message types.
    """

    while True:

        try:
            message, addr = serverSocket.recvfrom(2048)
            message = str.split(message.decode())
            print("\n\n")

            # put ack in container for checking
            if message[0] == "received_ack":
                ack_container.add(message[1])
                print("ack_container is: ", ack_container)

            # Put all other messages in the queue for processing.
            else:
                received_requests.put((message, addr))
                print(" received_requests is: ", message)


        except Exception as err:
            print('Unexpected error in server', type(err), str(err))
def validate_ip_address(address):
    try:
        ip = ipaddress.ip_address(address)
        # print("IP address {} is valid. The object returned is {}".format(address, ip))
        return True
    except ValueError:
        print("IP address {} is not valid".format(address))
        return False
# def validate_input(args, serverPort):
#     if len(args) != 3:
#         print("Usage: ChatApp.py -s <port>")
#         return False
#     elif serverPort < 1024 or serverPort > 65535:
#         print("correct server port number range: [1024,65535]")
#         return False
#     return True
def update_table(name, serverTable,clientAddress,channel):

    if name not in serverTable.keys():

        new_client = Client(clientAddress[0], clientAddress[1], name, "active")
        serverTable[name] = new_client
        channel[name] = "active"

        # send string back to client
        sendtoString = ("registered " + "[Welcome, You are registered.]").encode()
        serverSocket.sendto(sendtoString, clientAddress)
        # broadcast the complete table of active clients to all the online clients
        broadcast(name, serverTable, new_client)

        return serverTable
    else:
        sendtoString = ("duplicated " + "Nick name already exist, please choose a different one").encode()
        serverSocket.sendto(sendtoString, clientAddress)
def update_table_offline(name, serverTable,channel):
    # change status to "offline"
    serverTable[name].status = "offline"
    channel[name] = "offline"

    # broadcast the updated table to all the active (online) clients
    for nickName, client in serverTable.items():
        # print("serverTable item: ",nickName, client.status)
        if client.status == "active":
            sendto_string = ("offline_broadcast" +" " + name).encode()
            sendto_addr = (client.ip,client.port)
            serverSocket.sendto(sendto_string, sendto_addr)
def send_dereg_ack(name,serverTable):
    # send an ack to the client which requested de-registration
    sendto_string = "dereg_ack [You are Offline. Bye.]".encode()
    sendto_addr = (serverTable[name].ip, serverTable[name].port)
    serverSocket.sendto(sendto_string, sendto_addr)
def broadcast(name, serverTable, new_client):
    for n, serverTable_item in serverTable.items():
        # broadcast the serverTable to all clients

        sendtoString = ("BROADCAST " + str(new_client.ip) + " " + str(new_client.port) + " " + new_client.nickName + " " + new_client.status).encode()
        sentoAddr = (serverTable_item.ip, serverTable_item.port)
        serverSocket.sendto(sendtoString, sentoAddr)

        if serverTable_item.nickName != new_client.nickName:
            sendtoString = ("BROADCAST " + str(serverTable_item.ip) + " " + str(
                serverTable_item.port) + " " + serverTable_item.nickName + " "
                            + serverTable_item.status).encode()
            sentoAddr = (new_client.ip, new_client.port)
            serverSocket.sendto(sendtoString, sentoAddr)
def update_table_online(name, serverTable, serverSocket,channel,saved_msg):
    serverTable[name].status = "active"
    channel[name] = "active"
    #check for offline msgs:
    if name in saved_msg.keys():
        # send [You have messages] to client
        sendto_str = "offline_msg0 [You have messages]"
        sendto_addr = (serverTable[name].ip, serverTable[name].port)
        serverSocket.sendto(sendto_str.encode(),sendto_addr)
        #send msgs to client
        for msg in saved_msg[name]:
            print("offline msg", msg)
            sendto_str = ("offline_msg " + msg).encode()
            print("sendto_str", sendto_str)

            serverSocket.sendto(sendto_str,sendto_addr)
        #clear msg in server
        saved_msg.pop(name)

    #broadcast to all the clients that the user is back online
    for n, client in serverTable.items():
        sendto_str = "online_broadcast " + name
        serverSocket.sendto(sendto_str.encode(),(client.ip,client.port))



def runClient():
    # register each new client
    client = register(nickName, serverIp, serverPort, clientPort)
    # multiple clients implementation
    x = threading.Thread(target=ClientListen, args=(client, clientSocket, clientTable,))
    x.start()

    # while the client types in anything
    while True:
        # chat()
        client_input = input()
        message = client_input
        client_input = str.split(client_input)

        if len(client_input) == 0:
            continue

        if client.status == "offline":

            if client_input[0] == "reg":
                if len(client_input) == 2:
                    if client_input[1] == nickName:
                        client.status = "active"
                        sendto_string = message.encode()
                        clientSocket.sendto(sendto_string, (serverIp, serverPort))
                    else:
                        print("[please log back using your name:", nickName, "]")

                else:
                    print("[Usage: reg <name>]")
            else:
                continue
        else:
            # If the client wants to send messages
            if client_input[0] == "reg":
                print("[You are already online]")

            if client_input[0] == "send":
                if len(client_input) < 3:
                    print("[Usage: send <name> <message>]")
                else:
                    # if client sends msg
                    receiver = client_input[1]
                    if receiver in clientTable.keys():
                        # print("receiver exist")
                        # sends msg to receiver
                        sendto_addr = (clientTable[receiver].ip, int(clientTable[receiver].port))
                        sendto_string = (message + " " + nickName).encode()
                        lock = threading.Lock()
                        lock.acquire()

                        clientSocket.sendto(sendto_string, sendto_addr)

                        # Monitors if the receiver sends ack back
                        ready = select.select([clientSocket], [], [], 0.5)
                        # print("ready: ",ready[0])
                        if len(ready[0]) == 0:
                            count = 0
                            # no ack from client, send message to server to be displayed to client later
                            print("[No ACK from", receiver, "message sent to server.]")
                            msg = client_input[2:]
                            msg = ' '.join(msg)
                            date_time = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                            sendto_string = "save_msg " + nickName + " " + receiver + " " + " " + date_time + " " + msg
                            sendto_addr = (serverIp, serverPort)
                            while count < 5:
                                msg = sendto_string
                                # check if the server is also responding to request
                                # print("retrying..")
                                clientSocket.sendto((msg + " retry").encode(), sendto_addr)
                                msg = " "
                                ready = select.select([clientSocket], [], [], 0.5)
                                if len(ready[0]) == 0:
                                    count += 1
                                else:
                                    break
                            if count == 5:
                                print("[Server not responding]")
                                print("[Exiting]")
                                os._exit(1)
                            lock.release()
                    else:
                        print(receiver, "doesn't exist")

            elif client_input[0] == "dereg":
                if len(client_input) != 2:
                    print("[Usage: dereg <name>]")
                else:
                    # if client deregister
                    user = client_input[1]
                    if user != nickName:
                        print("please enter your correct name: ", nickName)
                    else:
                        count = 0
                        # send msg to server
                        sendto_addr = (serverIp, serverPort)
                        sendto_string = " " + message
                        lock = threading.Lock()
                        lock.acquire()
                        ready = select.select([clientSocket], [], [], 0.5)

                        while count < 5:
                            # print("retrying")
                            msg = sendto_string
                            clientSocket.sendto((msg + " retry").encode(), sendto_addr)
                            msg = " "
                            ready = select.select([clientSocket], [], [], 0.5)
                            if len(ready[0]) == 0:
                                count += 1
                            else:
                                break
                        if count == 5:
                            print("[Server not responding]")
                            print("[Exiting]")
                            os._exit(1)
                        lock.release()

            elif client_input[0] == "send_all":
                if len(client_input) < 2:
                    print("[Usage: send_all <message>]")
                else:
                    # forward message to server to broadcast to everyone else
                    sendto_addr = (serverIp, serverPort)
                    sendto_string = message + " " + nickName

                    clientSocket.sendto(sendto_string.encode(), sendto_addr)
                    # implement timeout again
                    lock = threading.Lock()
                    lock.acquire()
                    ready = select.select([clientSocket], [], [], 0.5)
                    if len(ready[0]) != 0:
                        print("[Message received by Server.]")
                    # time_out(ready, sendto_string,sendto_addr)
                    else:
                        count = 0
                        while count < 5:
                            # print("retrying")
                            msg = sendto_string
                            clientSocket.sendto((msg + " retry").encode(), sendto_addr)
                            msg = " "
                            ready = select.select([clientSocket], [], [], 0.5)
                            if len(ready[0]) == 0:
                                count += 1
                            else:
                                break
                        if count == 5:
                            print("[Server not responding]")
                            print("[Exiting]")
                            os._exit(1)
                        lock.release()

def validate_input_client(args):
    if len(args) != 6:
        print("Usage: ChatApp.py -c <name> <server-ip> <server-port> <client-port>")
    else:
        nickName, serverIp, serverPort, clientPort = args[2], args[3], int(args[4]), int(args[5])
        # validate ip addr
        isvalid_ip = validate_ip_address(serverIp)
        #validate port numbers
        if serverPort < 1024 or serverPort > 65535 or clientPort < 1024\
                or clientPort > 65535:
            print("correct port number range: [1024,65535]")
        elif isvalid_ip is True:
            return True

    return False
def register(nickName, serverIp, serverPort, clientPort):
    """
    sends REGISTRATION request to the server for booking keeping
    """
    sendtoString = ("REGISTRATION " + nickName).encode()
    clientSocket.sendto(sendtoString, (serverIp, serverPort))

    Message, serverAddress = clientSocket.recvfrom(2048)
    serverMessage = Message.decode().split(' ')
    # serverMessage = ' '.join(serverMessage[1:])
    # print("serverMessage: ",serverMessage)
    if serverMessage[0] == "registered":
        print(' '.join(serverMessage[1:]))
    if serverMessage[0] == "duplicated":
        print(' '.join(serverMessage[1:]))
        exit(1)

    client = Client(gethostbyname(gethostname()), clientPort, nickName, "active")

    return client
def update_clientTable(name, message):
    """

    :return:
    """
    client = Client(message[1], message[2], message[3], message[4])
    clientTable[name] = client
    print("[Client table updated.]")
    # print("[Client table has users:",clientTable.keys()," ]")


    return clientTable
def ClientListen(client, clientSocket, clientTable):
    while True:
        message, addr = clientSocket.recvfrom(2048)
        message = str.split(message.decode())
        if client.status == "active":
            if message[0] == "BROADCAST":
                name = message[3]
                clientTable = update_clientTable(name, message)

            # receives message from other client
            elif message[0] == "send":
                sender = message[-1]
                info = message[2:-1]
                info = ' '.join(info)
                # show message
                print(sender,":",info)
                sendto_addr = (clientTable[sender].ip, int(clientTable[sender].port))
                ack = "ACK [Message received by " + message[1] + "]"
                # send ACK to clients
                clientSocket.sendto(ack.encode(), sendto_addr)

            elif message[0] == "ACK":
                info = " ".join(message[1:])
                print(info)

            # receives a de-registration ack from server
            elif message[0] == "dereg_ack":
                client.status = "offline"
                print(" ".join(message[1:]))

            # receives a "successfully saved message" ack from server
            elif message[0] == "savedmsg_ack":
                print(" ".join(message[1:]))

            # receives an offline message ack from server
            elif message[0] == "offline_msg0":
                print("[You have messages]")
            elif message[0] == "offline_msg":
                message = " ".join(message[1:])
                print(message)

            # receives a table update from server
            elif message[0] =="offline_broadcast":
                print("[client table updated.]")
            # receives a table update from server
            elif message[0] == "online_broadcast":
                name = message[1]
                clientTable[name].status = "active"
                print("[client table updated.]")

            # receives a channel message from server
            elif message[0] == "Channel_Message":
                receiver = message[-1]
                sender = message[1]
                msg = message[:len(message)-1]

                # send back to server ack that channel message has been received
                sento_str = ("received_ack "+receiver).encode()
                sendto_addr = (serverIp,serverPort)

                clientSocket.sendto(sento_str,sendto_addr)
                msg = " ".join(msg)
                print(msg)

            elif message[0] =="ACK_GROUP":
                print("[Message received by Server.]")
                pass
def time_out(ready,sendto_string,sendto_addr):




    if len(ready[0]) == 0:
        # retry 5times:
        count = 0
        while count < 5 and len(ready[0]) == 0:
            # print("retrying...")
            msg = sendto_string + " retry"
            clientSocket.sendto(msg.encode(), sendto_addr)
            msg = " "
            ready = select.select([clientSocket], [], [], 0.5)
            count += 1

    if len(ready[0]) == 0:
        print("[Server not responding]")
        print("[Exiting]")
        exit(1)

if __name__ == '__main__':
    # run server mode
    if len(sys.argv) == 3 and sys.argv[1] == '-s':
        serverPort = int(sys.argv[2])
        input_isValid = validate_input(sys.argv, serverPort)
        if input_isValid is True:
            try:
                # create UDP socket
                serverSocket = socket(AF_INET, SOCK_DGRAM)
                # bind socket to local port
                serverSocket.bind(('', serverPort))
                print("The server is ready to receive")
                runServer()
            except Exception as err:
                print('Unexpected error in server', type(err), str(err))

    elif len(sys.argv) == 6 and sys.argv[1] == '-c':
        try:
            input_isValid = validate_input_client(sys.argv)
            if input_isValid:
                nickName, serverIp, serverPort, clientPort = sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
                clientTable = dict()
                # create UDP socket
                clientSocket = socket(AF_INET, SOCK_DGRAM)
                runClient()

        except KeyboardInterrupt:
            clientSocket.sendto(("CLOSE " + nickName).encode(), (serverIp, serverPort))
            print("closing a client")
            os._exit(1)
    else:
        print("Run Server: python3 ChatApp.py -s <port>")
        print("Run Client: python3 ChatApp.py -c <name> <server-ip> <server-port> <client-port>")






