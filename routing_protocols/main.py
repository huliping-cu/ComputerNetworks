#! /usr/bin/python3
import threading
from socket import *
import socket
import time

from routenode import *


localhost = "127.0.0.1"

class Node:

    # Initialize the node with routing table and list of neighbors, also bind the socket
    def __init__(self, port, neighbors,seen_ports,cost_change,mode):                
        self.port = port
        self.neighbors = neighbors
        self.seen_ports = seen_ports
        self.ip = localhost
        self.routingTable = {}                
        self.nexthop = {}
        self.first_time = True
        self.cost_change = cost_change
        self.mode = mode

        # create UDP socket
        self.socket = socket.socket(AF_INET, SOCK_DGRAM)
        # bind socket to local port
        self.socket.bind(('', self.port))
        print("The node is ready to receive")
    

    def wait_to_trigger(self):
        """
        change the cost of the link associated with the 
        neighbor with highest port number to <cost-change>
        """
        print("wait for 30's")
        time.sleep(5)
        chosen_neighbor = sorted(self.neighbors.items(),reverse = True).pop(0)
        chosen = chosen_neighbor[0]
        # print("\n")
        # print("\n")
        # print("\n")
        # print("chosen: ", chosen)
        self.neighbors[chosen] = self.cost_change
        # print(" self.neighbors: ",  self.neighbors)
        print('[{}] Node {} cost updated to {}'.format(time.time(),chosen,self.cost_change))
        msg = 'cost_change [{}]'.format(time.time())
        msg += " " + str(self.port) + "," + str(self.cost_change)
        self.socket.sendto(msg.encode(),(self.ip,chosen))
        print('[{}] Link value message sent from Node {} to Node {}'.format(time.time(),self.port,chosen_neighbor[0]))
        change = self.DistanceVectorAlgo()
        self.update_routingtable(change)


    def update_routingtable(self, change):        
        
        # print("change: ", change)
        # # print("\n")
        if change:
            print('routing updated!')
            # i = input('continue to send')
            
            self.broadcast()
            # print("routingTable: ",self.routingTable)

        elif self.first_time == True:
            self.first_time = False
            # print("sending DV for the first time!")
            self.broadcast()
            # print("routingTable: ",self.routingTable)
        
        else:
            pass
            # print('no DV update')
        self.print_table()

    
    
    def DistanceVectorAlgo(self):
        """
        for each destination y, node x also determines v*(y) (nexthop) and updates its forwarding table 
        for destination y.
        
        """
        change = False
        for destination in self.seen_ports:
            # print("\n")
            # print("destination: ",destination)
            if destination == self.port:
                # print("skip self")
                pass
            else:
               
                dv = self.routingTable[self.port]

                if destination in dv.keys():
                    old_hop = self.nexthop[destination]
                    old_cost = dv[destination]
                else:
                    old_hop = None
                    old_cost = float("inf")
                
                new_hop = None
                new_cost = float("inf")
                # print("old_hop: ",old_hop,"old_cost: ", old_cost)
                for neighbor, c in self.neighbors.items():
                    
                    if neighbor in self.routingTable.keys() and destination in self.routingTable[neighbor].keys():
                        # print("neighbor is: ", neighbor,"cost is: ",c)
                        d_v_y = float(self.routingTable[neighbor][destination])
                        distance = int(c) + d_v_y
                        if distance < new_cost:
                            new_hop = neighbor
                            new_cost = distance
                        # print("hop is: ", new_hop, "cost is: ", new_cost)

                # print("new_hop: ",new_hop,"new_cost: ", new_cost)


                if float(old_cost) != float(new_cost):
                    #update cost
                    dv[destination] = float(new_cost)
                    #update next hop to destination
                    self.nexthop[destination] = new_hop
                    change = True

                # print('new_hop: {}, new_cost: {}'.format(self.nexthop[destination], dv[destination]))
        
                        



        print("----------------------------------------")
        return change


    def update_table(self,msg,sender):
        if msg[0] == "routingTable_update":
            print('\n')
            # print("----------------------------------------")
            # print('sender: {} ,self:{} '.format(sender,self.port))

            # print('sender dv: {}'.format(self.routingTable[sender]))
            #incoming routingTable
            self.routingTable[int(sender)] = {}
            # print('sender dv now: {}'.format(self.routingTable[int(sender)]))

            #updating routing table upon receipt of new routingTable_update request
            sender_view = msg[2:] 
            # print("sender_view: ",sender_view)
            while len(sender_view) != 0:
                pair = sender_view.pop()
                # print("pair.split(','): ",pair.split(','))
                router = int(pair.split(',')[0])
                cost = float(pair.split(',')[1])
                self.routingTable[int(sender)][router] = cost
                # print(router,cost)
                if router not in self.seen_ports:
                    self.seen_ports.add(router)
                    change = True
            print('{} Message received at Node {} from Node {}'.format(msg[1],self.port,sender))
            # print("self.routingTable: ",self.routingTable)
            # print('\n')
            # print(self.seen_ports)
            
            # see if there's any change to local routing table upon receipt of new routingTable_update request
            # print("routingTable: ",self.routingTable)

            change = self.DistanceVectorAlgo()
            self.update_routingtable(change)    
        if msg[0] == "cost_change":
            # print("\n")
            

            # print("msg: ",msg)
            t = msg[1]
            # print("t: ",t)
            pair = msg[-1]
            # print("pair: ",pair)
            new_cost = float(pair.split(',')[1])
            # print("cost_change is: ", new_cost)

            print('[{}] Link value message received at Node {} from Node {}'.format(t,self.port,sender))
            self.neighbors[sender] = float(new_cost)
            # print('{} neighbors after receiving cost_change: '.format(self.port,self.neighbors))
            change = self.DistanceVectorAlgo()
            self.update_routingtable(change)  
            

    def print_table(self):
        
        print('[{}] Node {} Routing Table'.format(time.time(),self.port))
        
        for router in sorted(list(self.seen_ports)):
            cost = self.routingTable[self.port][router]
            if router == self.port:
                pass
            else:
                hop = self.nexthop[router]
                if hop != router:
                    print('- ({}) -> Node {}; Next hop -> Node {}'.format(cost, router, hop))
                else:
                    print('- ({}) -> Node {}'.format(cost, router))


        

    def listen(self):
        # print("\n",'listening')
        while True:
            message, senderaddr = self.socket.recvfrom(2048)
            message = message.decode()
            # print("\n")
            # print('Received {} from {}!'.format(message,senderaddr))
            msg = message.split(' ')
            sender = senderaddr[1]
            # print("sender: ",sender)
            if msg[0] == "routingTable_update":
                threading.Thread(target=self.update_table, args=(msg, sender,)).start()
            if msg[0] == "cost_change":
                # print("\n")
                # print('sender: {}, msg:{} '.format(sender, msg))
                # print("\n")
                threading.Thread(target=self.update_table, args=(msg, sender,)).start()
                



    #braodcast the new routing_table to every node
    def broadcast(self):
        print("\n")
        # print("----------------------------------------")
        for receiver, x in self.neighbors.items():    
            print("receiver is:",receiver)
            msg = 'routingTable_update [{}]'.format(time.time())
            for port, c in self.routingTable[self.port].items():
                # print("port: ",port, "type: ", type(port))
                if self.mode == 'p' and  port!= receiver and self.nexthop.get(port) == receiver:
                    c = float("inf")
                    print('[%s] Message sent from Node %s to Node %s with distance to Node %s as inf' % (
                        time.time(), self.port, receiver, port))

                msg += " " + str(port) + "," + str(c)
            self.socket.sendto(msg.encode(),(self.ip,receiver))
        
            print('[{}] Message sent from Node {} to Node {}'.format(time.time(), self.port, receiver))
            print('Message sent is: {}'.format(msg))
            print("\n")
        # # print("----------------------------------------")
        









def initialize_routingTable(node):
    # distance vector of self to all the neighbors
    node.routingTable[node.port] = {}
    node.routingTable[node.port][node.port] = float(0)
    for port, cost in node.neighbors.items():        
        node.routingTable[node.port][port] = float(cost) #distance from self to neighbor
        node.nexthop[port] = port #next hop to neighbor is just neighbor
        node.routingTable[port] = {port: float(0)} #routingTable of neighbor is all 0

    # print("node.routingTable: ", node.routingTable)
    # print("\n")

        


def validate_port(seen_ports):
    for port in seen_ports:
        # if port < 1024 or port > 65535:
        if port < 0 or port > 65535:
            print("correct port number range: [1024,65535]")
            return False
    return True