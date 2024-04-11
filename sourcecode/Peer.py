import random
import logging
from copy import deepcopy
from typing import Union

from Transaction import Transaction
from Block import Block
from utils import expon_distribution, generate_random_id
from Block import BlockChain
from DiscreteEventSim import simulation, Event, EventType
from Link import Link

from config import CONFIG

logger = logging.getLogger(__name__)


class Peer:

    def __init__(self, id, is_slow_network=False, is_slow_cpu=False):
        # self.id: int = id
        self.id: str = generate_random_id(3)
        self.is_slow_network: float = is_slow_network
        self.is_slow_cpu: float = is_slow_cpu
        self.crypto_coins: int = CONFIG.INITIAL_COINS
        self.neighbours: dict["Peer", any] = {}
        self.neighbours_meta: dict["Peer", Link] = {}
        self.cpu_power: float = self.__calculate_cpu_power()

        self.forwarded_messages: set[Union[Transaction, Block]] = set()

    @property
    def cpu_net_description(self):
        desc_cpu = "slow" if self.is_slow_cpu else "fast"
        desc_net = "slow" if self.is_slow_network else "fast"
        desc_cpu = desc_cpu+f" ({round(self.cpu_power, 2)})%"

        return f"CPU: {desc_cpu}, Net: {desc_net}"

    def __calculate_cpu_power(self) -> float:
        num_peers = CONFIG.NUMBER_OF_PEERS
        z1 = CONFIG.Z1
        deno = (10-9*z1)*num_peers
        neu = 1
        low_cpu_power = round(neu/deno, 4)
        high_cpu_power = round(10*low_cpu_power, 4)
        return low_cpu_power if self.is_slow_cpu else high_cpu_power

    def init_blockchain(self, peers: list["Peer"]):
        self.block_chain = BlockChain(cpu_power=self.cpu_power,
                                      broadcast_block_function=self.broadcast_block,
                                      peers=peers,
                                      owner_peer=self)

    def connect(self, peer: "Peer", link: Link):
        # self.connected_peers.append(peer)
        self.neighbours[peer] = link.get_link(self)
        self.neighbours_meta[peer] = link

    def disconnect(self, peer):
        # self.connected_peers.remove(peer)
        self.neighbours.pop(peer)

    @ property
    def __dict__(self) -> dict:
        return ({
            "id": self.id,
            "cpu_power": self.cpu_power,
            "is_slow_network": self.is_slow_network,
            "is_slow_cpu": self.is_slow_cpu,
            "crypto_coins": self.crypto_coins,
            "neighbours": [{neighbour.__repr__(): link.__dict__} for (neighbour, link) in self.neighbours_meta.items()],
            "block_chain": self.block_chain.__dict__,
            "cpu_net_description": self.cpu_net_description,
            "longest_chain_contribution": self.block_chain.longest_chain_contribution,
        })

    def description(self) -> str:
        return f"Peer(id={self.id} cpu_power={self.cpu_power} is_slow_network={self.is_slow_network} is_slow_cpu={self.is_slow_cpu})"

    def __repr__(self):
        return f"Peer(id={self.id})"

    def __forward_msg_to_peer(self, msg: Union[Transaction, Block], peer: "Peer"):
        self.neighbours[peer](msg)

    def __forward_msg_to_peers(self, msg: Union[Transaction, Block], peers: list["Peer"]):
        '''
        Forward a message to given peers.
        '''
        self.forwarded_messages.add(msg.id)

        for peer in peers:
            self.__forward_msg_to_peer(msg, peer)

    @ property
    def connected_peers(self):
        return list(self.neighbours.keys())

    def __create_txn(self, timestamp):
        to_peer = random.choice(self.connected_peers)
        amount = random.uniform(0, self.crypto_coins)
        self.crypto_coins -= amount
        return Transaction(self, to_peer, amount, timestamp)

    def generate_random_txn(self, timestamp):
        '''
        Generate a random transaction and broadcast it to all connected peers.
        '''
        # timestamp = simulation.clock
        new_txn = self.__create_txn(timestamp)
        self.block_chain.add_transaction(new_txn)
        new_txn_event_description = f"{self.id}->*; {new_txn};"
        new_txn_event = Event(EventType.TXN_BROADCAST, timestamp,
                              timestamp, self.broadcast_txn, (new_txn,), new_txn_event_description)
        simulation.enqueue(new_txn_event)

    def receive_msg(self, msg: Union[Transaction, Block], source: "Peer"):
        '''
        Receive a message from another peer.
        validate the message
        forward the message to other peers if needed* avoid loop
        '''
        if msg.id in self.forwarded_messages:
            return

        if isinstance(msg, Transaction):
            self.block_chain.add_transaction(msg)
        else:
            # logger.debug(f"Received block: {str(msg)}")
            self.block_chain.add_block(msg)

        self.__forward_msg_to_peers(
            msg, list(filter(lambda x: x != source, self.connected_peers)))

    def broadcast_msg(self, msg: Union[Transaction, Block]):
        '''
        Broadcast a message to all connected peers.
        '''
        self.__forward_msg_to_peers(msg, self.connected_peers)

    def broadcast_txn(self, txn):
        '''
        Broadcast a transaction to all connected peers.
        '''
        self.broadcast_msg(txn)

    def broadcast_block(self, block: Block):
        '''
        Broadcast a block to all connected peers.
        '''
        self.broadcast_msg(block)
