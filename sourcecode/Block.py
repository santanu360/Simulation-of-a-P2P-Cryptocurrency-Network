from typing import Any
import random
from copy import deepcopy
from functools import reduce
from Transaction import Transaction, CoinBaseTransaction
import logging
import hashlib

from config import CONFIG
from DiscreteEventSim import simulation, Event, EventType
from utils import expon_distribution, generate_random_id

logger = logging.getLogger(__name__)


class Block:

    def __init__(self, prev_block, transactions: list[Transaction], miner: any, timestamp: float):
        self.block_id: int = generate_random_id(4)
        self.prev_block: "Block" = prev_block
        self.transactions: list[Transaction] = transactions
        self.timestamp: float = timestamp
        self.miner: any = miner

        self.prev_block_hash = hash(prev_block) if prev_block else None

        logger.info(f"{self} <{EventType.BLOCK_CREATE}> {self.description()}")

    @property
    def id(self) -> int:
        return self.block_id

    @property
    def header(self) -> str:
        if self.block_id == 0:
            return hash("genesis block")
        if self.transactions == []:
            transaction_ids = "no transactions"
        else:
            transaction_ids = reduce(
                lambda a, b: a+b, map(lambda x: x.txn_id, self.transactions))
        return f"{self.block_id}-{self.prev_block_hash}-{self.timestamp}-{transaction_ids}"

    @property
    def num_txns(self) -> int:
        return len(self.transactions)

    def block_hash(self) -> int:
        return hashlib.sha256(self.header.encode()).hexdigest()

    def __repr__(self) -> str:
        return f"Block(id={self.block_id})"

    @property
    def __dict__(self) -> dict:
        dict_obj = {
            "self": self.__repr__(),
            "block_id": self.block_id,
            "prev_block": "",
            "self_hash": self.block_hash(),
            "miner": self.miner.__repr__(),
            "num_txns": self.num_txns,
            "transactions": sorted(list(map(lambda x: x.__dict__, self.transactions)), key=lambda x: x["txn_id"]),
            "timestamp": self.timestamp,
            "prev_block_hash": self.prev_block_hash
        }
        if self.prev_block:
            dict_obj.update({
                'prev_block': {
                    "id": self.prev_block.block_id,
                    "hash": self.prev_block.block_hash()
                }
            })
        return dict_obj

    def description(self) -> str:
        '''
        detailed description of block
        '''
        return f"Block id:{self.block_id} 󰔛:{self.timestamp} prev_block:{self.prev_block} txns:{self.transactions}"

    @property
    def size(self) -> int:
        '''
        size in kB
        '''
        return len(self.transactions)+1


def gen_genesis_block():
    '''
    Generate genesis block
    '''
    genesis_block = Block(None, [], None, 0)
    genesis_block.block_id = "gen_blk"
    return genesis_block


GENESIS_BLOCK = gen_genesis_block()


class BlockChain:

    def __init__(self, cpu_power: float, broadcast_block_function: Any, peers: list[Any], owner_peer: Any):
        self.__blocks: list[Block] = []
        self.__peer_id: Any = owner_peer
        self.__num_generated_blocks: int = 0
        self.__new_transactions: list[Transaction] = []
        self.__block_arrival_time: dict[Block, float] = {}
        self.__broadcast_block: Any = broadcast_block_function
        self.__mining_new_blocks: list[Block] = []
        self.__pending_generate_block: bool = False

        self.__longest_chain_length: int = 0
        self.__longest_chain_leaf: Block = None

        self.__branch_lengths: dict[Block, int] = {}
        self.__branch_balances: dict[Block, dict[Any, int]] = {}
        self.__branch_transactions: dict[Block, list[Transaction]] = {}
        self.__missing_parent_blocks: list[Block] = []

        self.avg_interval_time = CONFIG.AVG_BLOCK_MINING_TIME
        self.cpu_power: float = cpu_power

        self.__init_genesis_block(peers)

    @property
    def __dict__(self) -> dict:
        blocks = list(map(lambda x: x.__dict__, self.__blocks))
        blocks = sorted(blocks, key=lambda x: x["block_id"])
        block_arrival_times = list(map(lambda x: {x.__repr__(
        ): self.__block_arrival_time[x]}, self.__block_arrival_time))
        block_arrival_times = sorted(
            block_arrival_times, key=lambda x: list(x.values())[0])
        longest_chain = self.__get_longest_chain()
        longest_chain = list(map(lambda x: x.__repr__(), longest_chain))
        return {
            "blocks": blocks,
            "block_arrival_time": block_arrival_times,
            "longest_chain_length": self.__longest_chain_length,
            "longest_chain_leaf": self.__longest_chain_leaf.__repr__(),
            "avg_interval_time": self.avg_interval_time,
            "cpu_power": self.cpu_power,
            "longest_chain": longest_chain,
            "branches_info": self.branches_info,
        }

    @ property
    def peer_id(self) -> Any:
        return self.__peer_id

    def __repr__(self) -> str:
        return f"BlockChain(👥:{self.__peer_id})"

    def __init_genesis_block(self, peers: list[Any]):
        genesis_block = GENESIS_BLOCK
        self.__blocks.append(genesis_block)
        self.__longest_chain_length = 1
        self.__longest_chain_leaf = genesis_block
        self.__branch_lengths[genesis_block] = 1
        self.__branch_balances[genesis_block] = {}
        self.__branch_transactions[genesis_block] = []
        for peer in peers:
            self.__branch_balances[genesis_block].update(
                {peer: CONFIG.INITIAL_COINS})

    def __validate_block(self, block: Block) -> bool:
        '''
        1. validate all transactions
        2. transactions are not repeated
        '''
        prev_block = block.prev_block
        if prev_block not in self.__blocks:
            logger.info(
                "%s block_dropped %s previous block missing !!", self.peer_id, block)
            self.__missing_parent_blocks.append(block)
            return False
        if block in self.__blocks:
            logger.info(
                "%s block_dropped %s block already in blockchain !!", self.peer_id, block)
            return False
        for transaction in block.transactions:
            if not self.__validate_transaction(transaction, prev_block):
                logger.info(
                    "%s block_dropped %s invalid transaction !!", self.peer_id, block)
                return False
            if transaction in self.__branch_transactions[prev_block]:
                logger.info(
                    "%s block_dropped %s %s transaction already in blockchain!!", self.peer_id, block, transaction)
                return False

        # logger.debug(f"Block {block} is valid")
        return True

    def __validate_transaction(self, transaction: Transaction, prev_block: Block) -> bool:
        '''
        1. no balance of any peer shouldn't go negative
        '''
        balances_upto_block = self.__branch_balances[prev_block]
        if transaction.from_id and balances_upto_block[transaction.from_id] < transaction.amount:
            # logger.debug(f"Transaction {transaction} is invalid")
            return False

        # logger.debug(f"Transaction {transaction} is valid")
        return True

    def __update_chain_length(self, block: Block):
        prev_block = block.prev_block
        chain_len_upto_block = self.__branch_lengths[prev_block] + 1
        self.__branch_lengths[block] = chain_len_upto_block
        # self.__branch_lengths.pop(prev_block)
        # logger.debug(f"Chain length upto block {block} is {chain_len_upto_block}")

    def __update_balances(self, block: Block):
        prev_block = block.prev_block
        balances_upto_block = self.__branch_balances[prev_block].copy()
        for transaction in block.transactions:
            if transaction.from_id:
                balances_upto_block[transaction.from_id] -= transaction.amount
            balances_upto_block[transaction.to_id] += transaction.amount
        self.__branch_balances[block] = balances_upto_block
        # self.__branch_balances.pop(prev_block)
        # logger.debug(f"Balances upto block {block} are {balances_upto_block}")

    def __update_avg_interval_time(self, block: Block):
        return
        # prev_block = block.prev_block
        # num_blocks = len(self.__blocks)
        # if num_blocks == 1:
        #     return
        # interval_time = block.timestamp - prev_block.timestamp
        # self.avg_interval_time = (
        #     self.avg_interval_time * (num_blocks-1) + interval_time) / num_blocks
        # logger.debug("Avg interval updated %s", self.avg_interval_time)

    def __update_branch_transactions(self, block: Block):
        prev_block = block.prev_block
        prev_branch_txns = (self.__branch_transactions[prev_block]).copy()
        for transaction in block.transactions:
            prev_branch_txns.append(transaction)
        self.__branch_transactions[block] = prev_branch_txns

    def __update_block_arrival_time(self, block: Block):
        self.__block_arrival_time[block] = simulation.clock

    def __add_block(self, block: Block) -> bool:
        '''
        Add a block to the chain
        '''
        for transaction in block.transactions:
            # if transaction in self.__new_transactions:
            if isinstance(transaction, CoinBaseTransaction):
                continue
            if transaction in self.__new_transactions:
                self.__new_transactions.remove(transaction)

        self.__blocks.append(block)
        self.__update_chain_length(block)
        self.__update_balances(block)
        self.__update_block_arrival_time(block)
        self.__update_avg_interval_time(block)
        self.__update_branch_transactions(block)

    def __validate_saved_blocks(self):
        remove_blocks = []
        for block in self.__missing_parent_blocks:
            if self.__validate_block(block):
                remove_blocks.append(block)
                self.__add_block(block)
        for block in remove_blocks:
            self.__missing_parent_blocks.remove(block)

    def add_block(self, block: Block) -> bool:
        '''
        validate and then add a block to the chain
        '''
        if not self.__validate_block(block):
            return False

        self.__add_block(block)

        chain_len_upto_block = self.__branch_lengths[block]
        self.__validate_saved_blocks()
        if chain_len_upto_block > self.__longest_chain_length:
            logger.debug("%s <longest_chain> %s %s generating new block !!",
                         self.__peer_id,
                         str(self.__longest_chain_length), str(chain_len_upto_block))
            self.__longest_chain_length = chain_len_upto_block
            self.__longest_chain_leaf = block
            self.__generate_block()

    def add_transaction(self, transaction: Transaction) -> bool:
        '''
        Add a transaction to the chain
        '''
        # if transaction in self.__branch_transactions:
        # return
        self.__new_transactions.append(transaction)
        if transaction.from_id == self.__peer_id:
            return
        if self.__pending_generate_block and len(self.__new_transactions) >= CONFIG.BLOCK_TXNS_TRIGGER_THRESHOLD:
            self.__pending_generate_block = False
            self.__generate_block()

    def __mine_block_start(self, block: Block):
        delay = expon_distribution(self.avg_interval_time/self.cpu_power)

        new_event = Event(EventType.BLOCK_MINE_FINISH, simulation.clock, delay,
                          self.__mine_block_end, (block,), f"mining block finished {block}")
        simulation.enqueue(new_event)

    def __mine_block_end(self, block: Block):
        '''
        Broadcast a block to all connected peers.
        '''
        self.__mining_new_blocks.remove(block)
        self.__num_generated_blocks += 1
        if block.prev_block == self.__longest_chain_leaf and self.__validate_block(block):
            logger.info(
                "%s <%s> %s", self.__peer_id, EventType.BLOCK_MINE_SUCCESS, block)
            block.transactions.append(CoinBaseTransaction(
                self.__peer_id, block.timestamp))
            self.__add_block(block)
            new_event = Event(EventType.BLOCK_BROADCAST, simulation.clock, 0,
                              self.__broadcast_block, (block,), f"{self.__peer_id}->* broadcast {block}")
            simulation.enqueue(new_event)
        else:
            # no longer longest chain
            logger.info(
                "%s <%s> %s", self.__peer_id, EventType.BLOCK_MINE_FAIL, block)
        logger.info('restarting block minining')
        # self.__generate_block()

    def __generate_block(self) -> Block:
        '''
        Generate a new block
        '''
        sorted(self.__new_transactions, key=lambda x: x.timestamp)
        valid_transactions_for_longest_chain = []
        balances_upto_block = self.__branch_balances[self.__longest_chain_leaf].copy(
        )
        for transaction in self.__new_transactions:
            if balances_upto_block[transaction.from_id] < transaction.amount:
                continue
            balances_upto_block[transaction.from_id] -= transaction.amount
            balances_upto_block[transaction.to_id] += transaction.amount
            valid_transactions_for_longest_chain.append(transaction)

        if len(valid_transactions_for_longest_chain) < CONFIG.BLOCK_TXNS_MIN_THRESHOLD:
            logger.debug("<num_txns> not enough txns to mine a block !!",)
            self.__pending_generate_block = True
            return

        new_block = Block(self.__longest_chain_leaf,
                          valid_transactions_for_longest_chain,
                          self.peer_id, simulation.clock)
        self.__mining_new_blocks.append(new_block)
        new_event = Event(EventType.BLOCK_MINE_START, simulation.clock, 0,
                          self.__mine_block_start, (new_block,), f"attempt to mine block {new_block}")
        simulation.enqueue(new_event)

    def generate_block(self):
        self.__generate_block()

    def __get_longest_chain(self):
        chain = []
        cur_chain = self.__longest_chain_leaf
        while cur_chain.prev_block:
            chain.append(cur_chain)
            cur_chain = cur_chain.prev_block
        return chain

    def __get_leaf_blocks(self):
        '''
        return leaf blocks
        '''
        leaf_blocks = self.__blocks.copy()
        for block in self.__blocks:
            if block.prev_block in leaf_blocks:
                leaf_blocks.remove(block.prev_block)
        return leaf_blocks

    def __get_branches(self):
        '''
        return branch lengths
        '''
        leaf_blocks = self.__get_leaf_blocks()
        branch_lengths = []
        for block in leaf_blocks:
            branch_lengths.append({
                "leaf_block": block.__repr__(),
                "length": self.__branch_lengths[block]
            })
        return branch_lengths

    def __get_forks(self):
        '''
        return forks
        '''
        child_counts = {}
        for block in self.__blocks:
            prev_block = block.prev_block
            if not prev_block:
                continue
            if prev_block not in child_counts:
                child_counts[prev_block] = 0
            child_counts[prev_block] = child_counts[prev_block] + 1
        forks = []
        for block, child_freq in child_counts.items():
            if child_freq > 1:
                forks.append({
                    "fork_at": block.__repr__(),
                    "num_forks": child_freq
                })
        return forks

    @ property
    def branches_info(self):
        '''
        number of forks
        number of branches and their lengths
        '''
        branches = self.__get_branches()
        forks = self.__get_forks()

        return {
            "num_forks": len(forks),
            "num_branches": len(branches),
            "forks": forks,
            "branches": branches
        }

    @ property
    def longest_chain_contribution(self):
        count_longest_chain = 0
        for block in self.__get_longest_chain():
            if block.miner == self.__peer_id:
                count_longest_chain += 1

        if self.__num_generated_blocks == 0:
            return 0
        return round(count_longest_chain/self.__num_generated_blocks*100, 2)
