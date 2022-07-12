#! /usr/bin/python3

from socket import *
from main import *
from LSA import *
import sys


if __name__ == '__main__':
    # print("len is:", len(sys.argv))
    if len(sys.argv) >= 6:
        algo = sys.argv[1] # dv or ls
        mode = sys.argv[2] # r or p
        # print("mode is: ", mode)
        update_interval = sys.argv[3]
        selfport = int(sys.argv[4])
        input_info = sys.argv[5:]
        neighbors = {}  
        seen_ports = set()
        seen_ports.add(selfport)
        # python3 routenode.py dv r 123 1111 2222 1 3333 50
        if algo == "dv":
            if sys.argv[-1] != 'last' and sys.argv[-2] != 'last':
                if len(input_info) % 2 != 0: 
                    print("please input the correct neighbors information: port + distance")
                else:
                    while input_info:
                        port = int(input_info.pop(0))
                        seen_ports.add(port)                    
                        distance = input_info.pop(0)
                        neighbors[port] = distance
                # print("seen_ports",seen_ports)

                port_isValid = validate_port(seen_ports)

                if port_isValid is True:
                    # try:
                        print("not last")
                        node = Node(selfport,neighbors,seen_ports,None,mode)
                        print('port: {}, neighbors:{}, seen_ports:{}'.format(node.port, node.neighbors,node.seen_ports))
                        initialize_routingTable(node)
                        print('routingTable:{}'.format(node.routingTable))
                        node.listen()
                        
                        # threading.Thread(target=listen, args=(node,)).start()
                        
                    # except Exception as err:
                    #     print('Unexpected error', type(err), str(err))

            # python3 routenode.py dv r 123 4444 2222 8 3333 5 last
            elif  sys.argv[-1] == 'last':
                # print("input_info",input_info)

                if len(input_info) % 2 != 1: 
                    print("please input the correct neighbors information: port + distance")
                else:
                    input_info = input_info[:-1]

                    while input_info:
                        port = int(input_info.pop(0))
                        seen_ports.add(port)                    
                        distance = input_info.pop(0)
                        neighbors[port] = distance
                port_isValid = validate_port(seen_ports)
                if port_isValid is True:
                    # try:
                        node = Node(selfport,neighbors,seen_ports,None,mode)
                        initialize_routingTable(node)
                        # print('routingTable:{}'.format(node.routingTable))
                        node.broadcast()                
                        node.listen()

                    # except KeyboardInterrupt:
                    #     # clientSocket.sendto(("CLOSE " + nickName).encode(), (serverIp, serverPort))
                    #     print("closing a client")
                    #     os._exit(1)


            # python3 routenode.py dv r 123 4444 2222 8 3333 5 last
            elif  sys.argv[-2] == 'last':
                msg = input_info[:-2]
                print("msg",input_info[:-2])
                if len(input_info) % 2 != 0: 
                    print("please input the correct neighbors information: last + distance")
                else:
                    cost_change = input_info[-1]
                    #popped the cost_change
                    input_info.pop(-1)
                    #popped the "last" chars
                    input_info.pop(-1)
                    # print("input_info",input_info)

                    while input_info:
                        port = int(input_info.pop(0))
                        seen_ports.add(port)                    
                        distance = input_info.pop(0)
                        neighbors[port] = distance
                        # print('port:{} seen_ports:{} distance:{} neighbors:{}'.format(port,seen_ports,distance,neighbors))
                port_isValid = validate_port(seen_ports)
                if port_isValid is True:
                    # try:
                        node = Node(selfport,neighbors,seen_ports,cost_change,mode)
                        initialize_routingTable(node)
                        print('routingTable:{}'.format(node.routingTable))
                        node.broadcast()
                        # because there's link change, start a new thread to deal with ...
                        # without impeding the node from receiving other requests
                        threading.Thread(target = node.wait_to_trigger).start()

                        node.listen()


                    # except KeyboardInterrupt:
                    #     # clientSocket.sendto(("CLOSE " + nickName).encode(), (serverIp, serverPort))
                    #     print("closing a client")
                    #     os._exit(1)
        else:
            lsa_table = {}
            if sys.argv[-1]  == 'last':
                last = 1
                cost_change = None
                input_info = input_info[:-1]
                while input_info:
                    port = int(input_info.pop(0))
                    seen_ports.add(port)                    
                    distance = input_info.pop(0)
                    neighbors[port] = float(distance)
            elif sys.argv[-2] == 'last':
                last = 1
                cost_change = input_info[-1]
                #popped the cost_change
                input_info.pop(-1)
                #popped the "last" chars
                input_info.pop(-1)
                # print("input_info",input_info)

                while input_info:
                    port = int(input_info.pop(0))
                    seen_ports.add(port)                    
                    distance = input_info.pop(0)
                    neighbors[port] = float(distance)
            else:
                last = 0
                cost_change = None
                while input_info:
                        port = int(input_info.pop(0))
                        seen_ports.add(port)                    
                        distance = input_info.pop(0)
                        neighbors[port] = float(distance)

            port_isValid = validate_port(seen_ports)
            lsa_table[selfport] = neighbors
            # print('self: {}, seen_ports:{}, neighbors:{}, cost_change: {}'.format(selfport, seen_ports, lsa_table,cost_change))



                
            if port_isValid is True:                
                # print("update_interval: ",update_interval)
                print("cost chanage:",cost_change)
                node = Node_ls(selfport,lsa_table,seen_ports,cost_change,mode,update_interval,last)


                    

    
                            

    else:
        print("Run Server: python3 ChatApp.py -s <port>")
        print("Run Client: python3 ChatApp.py -c <name> <server-ip> <server-port> <client-port>")




