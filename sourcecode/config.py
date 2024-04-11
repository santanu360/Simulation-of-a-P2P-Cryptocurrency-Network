class CONFIG:
    '''
    Simulation configuration
    '''
    SAVE_RESULTS = False  # save results to a file

    # parameters as mentioned in the papers
    NUMBER_OF_PEERS = 20
    Z0 = 0.7  # network z0 is slow
    Z1 = 0.8  # cpu z1 is slow
    AVG_TXN_INTERVAL_TIME = 10*1000
    AVG_BLOCK_MINING_TIME = 1000*1000  # avg block interval time (ms)

    # tuning parameters
    TARGET_NUM_BLOCKS = 300
    TXN_PER_BLOCK = 100

    ############################
    # no need to change below
    ############################

    # derived parameters
    TOTAL_NUM_BLOCKS = TARGET_NUM_BLOCKS
    TOTAL_NUM_TRANSACTIONS = TARGET_NUM_BLOCKS*TXN_PER_BLOCK
    TXN_PER_PEER = TOTAL_NUM_TRANSACTIONS/NUMBER_OF_PEERS

    BLOCK_TXNS_MAX_THRESHOLD = 1000  # 1020
    BLOCK_TXNS_MIN_THRESHOLD = min(50, TXN_PER_BLOCK)
    BLOCK_TXNS_TRIGGER_THRESHOLD = TXN_PER_BLOCK
    # mean of exponential time interval bw transactions (ms)
    INITIAL_COINS = 1000
    EVENT_QUEUE_TIMEOUT = 5

    @property
    def __dict__(self) -> dict:
        return ({
            "SAVE_RESULTS": self.SAVE_RESULTS,
            "NUMBER_OF_PEERS": self.NUMBER_OF_PEERS,
            "Z0": self.Z0,
            "Z1": self.Z1,
            "AVG_TXN_INTERVAL_TIME": self.AVG_TXN_INTERVAL_TIME,
            "AVG_BLOCK_MINING_TIME": self.AVG_BLOCK_MINING_TIME,
            "TARGET_NUMBER_OF_BLOCKS": self.TARGET_NUM_BLOCKS,
            "NUMBER_OF_TXNS_PER_BLOCK": self.TXN_PER_BLOCK,
            "NUMBER_OF_TRANSACTIONS": self.TOTAL_NUM_TRANSACTIONS,
            "NUMBER_OF_TRANSACTIONS_PER_PEER": self.TXN_PER_PEER,
            "BLOCK_TXNS_MAX_THRESHOLD": self.BLOCK_TXNS_MAX_THRESHOLD,
            "BLOCK_TXNS_MIN_THRESHOLD": self.BLOCK_TXNS_MIN_THRESHOLD,
            "BLOCK_TXNS_TRIGGER_THRESHOLD": self.BLOCK_TXNS_TRIGGER_THRESHOLD,
            "INITIAL_COINS": self.INITIAL_COINS,
            "EVENT_QUEUE_TIMEOUT": self.EVENT_QUEUE_TIMEOUT,
        })
