#! /usr/bin/python3
from asyncio.streams import FlowControlMixin
import threading
from socket import *
import socket
import time
import random

from numpy import broadcast
from routenode import *


localhost = "127.0.0.1"

class Node_ls:

    # Initialize the node with routing table and list of neighbors, also bind the socket
    def __init__(self, port, neighbors,seen_ports,cost_change,mode, update_interval, last ):                
        self.port = port
        self.neighbors = neighbors   # lsa_table
        self.seen_ports = seen_ports
        self.ip = localhost
        self.topology_table = {} 
        self.nexthop = {}
        self.cost_change = cost_change
        self.mode = mode
        self.update_interval = int(update_interval)
        self.ROUTING_INTERVAL = 10
        self.last = last
        self.seqNum = 0
        self.prev_seqNum = {}
        self.start = 0
        self.ip = '127.0.0.1'
        # create UDP socket
        self.socket = socket.socket(AF_INET, SOCK_DGRAM)
        # bind socket to local port
        self.socket.bind(('', self.port))
        self.activated = False
        self.first_routing = False
        # print("# lsa_table: ", self.neighbors)
        self.update_topoTable()
        self.print_topo_table()
        
        # print("cost change: ",self.cost_change)
        if self.last == 1:
            self.start = 1
            threading.Thread(target=self.broadcast, args=("init", 0, self.port)).start()
            threading.Thread(target=self.pulseLSA, args=()).start()

            if self.cost_change is not None:
                # print("cost chanage:",cost_change)
                
                threading.Thread(target=self.trigger_cost_change).start()


            time.sleep(self.ROUTING_INTERVAL)
            self.Dijkstra()
            self.first_routing = True

        self.listen()

    def trigger_cost_change(self):
        """
        change the cost of the link associated with the 
        neighbor with highest port number to <cost-change>
        """
        print("wait for 30's")
        # print("self.neighbors: ", self.neighbors)
        time.sleep(1.2*self.ROUTING_INTERVAL)
        chosen = sorted(self.neighbors[self.port],reverse = True).pop(0)

        t = time.time()
        self.neighbors[self.port][chosen] = self.cost_change
        # self.neighbors[chosen][self.port] = self.cost_change
        print(f'[{t}] Node {chosen} cost updated to {self.cost_change}')

        #LSA: "cost_change", self.port，self.cost_change 
        send_to = "cost_change" + " " + str(self.cost_change)
        self.socket.sendto(send_to.encode(), (self.ip, chosen))

        print(f'[{t}] Link value message sent from Node {self.port} to Node {chosen}')

        changed = self.update_topoTable()
        if changed:
                #print network topology table
                self.print_topo_table()
 
        self.broadcast("other",self.seqNum,self.port)






    #broadcast the lSA packet
    def broadcast(self, header, seqNum, senderport):
        self.activated = True
        #LSA: header source, seqNum, routinginfo{n:c, n:c...}
        

        # sender configureing the lsa_pkt before broadcasting to all direct neighbors
        LSA_pkt = header + " " + str(senderport) +" "+ str(seqNum)
        for n, c in self.neighbors[self.port].items():
            LSA_pkt += " " + str(n)+","+str(c)

        #brodacasting to all direct neighbors to sender
        for receiver in self.neighbors[self.port].keys():
            print("\n")
            # print("receiver: ", receiver)
            addr = (self.ip, receiver)
            self.socket.sendto(LSA_pkt.encode(), addr)
            # print('LSA_pkt: {}'.format(LSA_pkt))
            print(f"[{time.time()}] LSA of Node {senderport} with sequence number {seqNum} sent to Node {receiver}")
        self.prev_seqNum[self.port] = self.seqNum
        self.seqNum += 1
        # print("self.prev_seqNum: ",self.prev_seqNum)

    def pulseLSA(self):
        while True:
            # print(self.update_interval+random.random())
            time.sleep(self.update_interval+random.random())
            self.broadcast("pulseLSA", self.seqNum, self.port)

     

    def update_topoTable(self):
        """
        update all the links info, if any link is outdated, return changed as True
        """
        # {(1111, 2222): cost
        changed = False

        for router, dv in self.neighbors.items():
            for n, c in dv.items():
                if n < router:
                    l,r = n, router
                else:
                    l,r = router, n
                edge = (l,r)
                if c != self.topology_table.get(edge):
                    self.topology_table[edge] = c
                    changed = True
        print("changed: ", changed)
        return changed

    def update_lsa_table(self, source, neighbor_info):
        """
         update local lsa_table 
        """
        if source not in self.neighbors.keys():     
            self.neighbors[source] = {}   
        while neighbor_info:
            n, c = neighbor_info.pop(0).split(",")
            n, c = int(n), float(c)
            # print(f'n: {n}, c: {c} ,c type: {type(c)}')
            if n not in self.seen_ports:
                    self.seen_ports.add(n)

            self.neighbors[source][n] = c

            if n not in self.neighbors.keys():     
                self.neighbors[n] = {}
            self.neighbors[n][source] = int(c)
        # print(f'self.neighbors: {self.neighbors}')                
        
    def print_topo_table(self):
        t = time.time()
        print(f'[{t}] Node {self.port} Network topology')
        links = sorted(list(self.topology_table))
        for link in links:
            print(f'- {self.topology_table[link]} from Node {link[0]} to Node {link[1]}')
        if self.first_routing:
                self.Dijkstra()

    def Dijkstra(self):
        # res = self.if_received_all_lsa()

        # initilization
        D = {}
        P = {}
        N_prime = set()
        N_prime.add(self.port)

        dv = self.neighbors[self.port]
        for v in self.seen_ports:
            if v in dv.keys():
                D[v] = dv[v]
                P[v] = self.port
            else:
                D[v] = float("inf")

        # loop
        while N_prime != self.seen_ports:

            min_val = float("inf")
            w = None
            for v in self.seen_ports:
                if v not in N_prime:
                    D[v] = int(D[v])
                    if float(D[v]) <= min_val:
                        min_val = D[v]
                        w = v
            N_prime.add(w)

            print("self.neighbors: ", self.neighbors)
            for v, cost in self.neighbors[w].items():
                if v not in N_prime:
                    if D[w] + cost < D[v]:
                        D[v] = D[w] + cost            
                        P[v] = w
        self.update_routing_table(D,P)



    def update_routing_table(self,D,P):
        print("TODO: UPDATE ROUTING")


    def receiving(self,source,neighbor_info,sender,seqNum,msg,message):
        """
        upon receiving of a new LSA pkt, check if any duplicate pkts, if it is older or
        duplicate, print status message and drop it by not excuting any of the code.

        IF it is new LSA pkt:
            - update the local lsa table and check if the topology has changed( i.e. 
        any link change, and if there is: print the new topo table, update routing table..)
            - forward the lsa pkt to it's own neighbors (not sender)
        
        
        """

        # PI Algorithm:  check if ineffect pkt is received 
        if source in self.prev_seqNum.keys() and self.prev_seqNum[source] >= seqNum:
            print(f"\n [{time.time()}] DUPLICATE LSA packet Received, AND DROPPED:")
            print(f"- LSA of node {source}")
            print(f"- Sequence number {seqNum}")
            print(f"- Received from {sender}")                
        
        else:  
            # new LSA from source
            print(f'[{time.time()}] LSA of Node {source} with sequence number {seqNum} received from Node {sender}')
            
            self.update_lsa_table(source, neighbor_info)

            # update topology upon ceceipt of new LSA
            changed = self.update_topoTable()
            if changed:
                #print network topology table
                self.print_topo_table()



            for key in self.neighbors[self.port].keys():
                if key != sender and key != source:
                    # print(f'msg: {msg}')
                    sendto_str = ' '.join(msg)
                    # print(f'sendto_str: {sendto_str}')
                    self.socket.sendto(sendto_str.encode(), (self.ip, key))
                    print('[%s] LSA of Node %s with sequence number %s sent to Node %s' % (
                        time.time(), source, seqNum, key))
            self.prev_seqNum[source] = seqNum

        if not self.activated:
            print("first time broadcasting")
            self.broadcast("init",seqNum,self.port)
            threading.Thread(target=self.pulseLSA, args=()).start()


    


        
    def listen(self):
        print('listening')
        while True:

            #LSA: header source, seqNum, routinginfo{n:c, n:c...}
            message, clientAddress = self.socket.recvfrom(2048)
            msg = message.decode().split(" ")
            header = msg[0]

            if header == "init" or header == "pulaseLSA":
                
                sender = clientAddress[1]
                source = int(msg[1])
                seqNum = float(msg[2])
                neighbor_info = msg[3:]
                t = time.time()
                # print(f"\n Received: {message} from {sender}")
                # print(f"{[t]} header: {header}, seqNum: {seqNum}, neighbor_info: {neighbor_info} ")
                

                threading.Thread(target=self.receiving, args=(source,neighbor_info,sender,seqNum,msg,message)).start()
            elif header == "cost_change":
                print("msg: ",msg)
                cost_change = msg[1]
                sender = clientAddress[1]
                print("cost change: ", cost_change, "sender: ", sender)

                threading.Thread().start()
 
                print(f'[{time.time()}] Link value message received at Node {self.port} from Node {sender}')
                # self.dv[self.port][sender] = int(cost)
                self.neighbors[self.port][sender] = int(cost_change)
                self.neighbors[sender][self.port] = int(cost_change)
                
                print(f'[{time.time()}] Node {sender} cost updated to {cost_change}')
                changed = self.update_topoTable()
                if changed:
                    #print network topology table
                    self.print_topo_table()
        
                self.broadcast("other",self.seqNum,self.port)

            else:
                threading.Thread(target=self.receiving, args=(source,neighbor_info,sender,seqNum,msg,message)).start()




def validate_port(seen_ports):
    for port in seen_ports:
        if port < 1024 or port > 65535:
        # if port < 0 or port > 65535:
            print("correct port number range: [1024,65535]")
            return False
    return True