import random
import json
import pickle
from time import time, strftime
from tqdm import tqdm

from logger import init_logger
from network import is_connected, create_network
from DiscreteEventSim import simulation, Event, EventType, HookType
from utils import expon_distribution, create_directory, change_directory, copy_to_directory, clear_dir
from visualisation import visualize

from config import CONFIG


logger = init_logger()
START_TIME = time()
START_TIME = strftime("%Y-%m-%d_%H:%M:%S")
config_instance = ''
peers_network = []
pbar_txns, pbar_blocks = None, None
free_tnx_counter = 0
blocks_broadcasted = 0


def log_peers(peers):
    '''
    print(peers)
    '''
    for peer in peers:
        logger.info("peer: %s", peer)
        logger.info("peer id: %s, neighbours: %s",
                    peer.id, peer.connected_peers)
    logger.info(is_connected(peers))


def schedule_transactions(peers):
    '''
    Schedule transactions
    '''
    time = 0
    while simulation.event_queue.qsize() < CONFIG.TOTAL_NUM_TRANSACTIONS:
        # Generate exponential random variable for interarrival time
        interarrival_time = expon_distribution(CONFIG.AVG_TXN_INTERVAL_TIME)
        # logger.debug(f"Interarrival time: {interarrival_time}")
        from_peer = random.choice(peers)
        new_txn_event = Event(EventType.TXN_CREATE, time,
                              time, from_peer.generate_random_txn, (time,), f"{from_peer} create_txn")
        time = time + interarrival_time
        simulation.enqueue(new_txn_event)


def calculate_ratios(peers):
    ratios = {
        'cpu_low': {
            'net_low': [],
            'net_high': [],
        },
        'cpu_high': {
            'net_low': [],
            'net_high': [],
        }
    }
    for peer in peers:
        if peer.is_slow_cpu:
            if peer.is_slow_network:
                ratios['cpu_low']['net_low'].append(
                    peer.block_chain.longest_chain_contribution)
            else:
                ratios['cpu_low']['net_high'].append(
                    peer.block_chain.longest_chain_contribution)
        else:
            if peer.is_slow_network:
                ratios['cpu_high']['net_low'].append(
                    peer.block_chain.longest_chain_contribution)
            else:
                ratios['cpu_high']['net_high'].append(
                    peer.block_chain.longest_chain_contribution)

    if len(ratios['cpu_low']['net_low']):
        ratios['cpu_low']['net_low'] = round(
            sum(ratios['cpu_low']['net_low'])/len(ratios['cpu_low']['net_low']), 2)
    else:
        ratios['cpu_low']['net_low'] = 0
    if len(ratios['cpu_low']['net_high']):
        ratios['cpu_low']['net_high'] = round(
            sum(ratios['cpu_low']['net_high'])/len(ratios['cpu_low']['net_high']), 2)
    else:
        ratios['cpu_low']['net_high'] = 0
    if len(ratios['cpu_high']['net_low']):
        ratios['cpu_high']['net_low'] = round(
            sum(ratios['cpu_high']['net_low'])/len(ratios['cpu_high']['net_low']), 2)
    else:
        ratios['cpu_high']['net_low'] = 0
    if len(ratios['cpu_high']['net_high']):
        ratios['cpu_high']['net_high'] = round(
            sum(ratios['cpu_high']['net_high'])/len(ratios['cpu_high']['net_high']), 2)
    else:
        ratios['cpu_high']['net_high'] = 0
    return ratios


def calculate_summary(peers):
    summary = []
    for peer in peers:
        info = peer.block_chain.branches_info
        summary.append({
            'peer': peer.__repr__(),
            'hash_power': peer.cpu_power,
            'network_slow': peer.is_slow_network,
            'ratio': peer.block_chain.longest_chain_contribution,
            'num_forks': info['num_forks'],
            'num_branches': info['num_branches'],
            'forks': info['forks'],
            'branches': info['branches'],
        })
    return summary


def export_data(peers):
    '''
    Export data to a file
    '''
    global config_instance
    raw_data = []
    json_data = []
    for peer in peers:
        json_data.append(peer.__dict__)
        raw_data.append(peer)
    json_data = {'peers': json_data}

    json_data['ratios'] = calculate_ratios(peers=peers)
    # json_data['config'] = CONFIG.__dict__
    json_data['summary'] = calculate_summary(peers=peers)

    if CONFIG.SAVE_RESULTS:
        output_dir = f"output/{START_TIME}"
        create_directory(output_dir)
        copy_to_directory('blockchain_simulation.log', output_dir)
        change_directory(output_dir)
    clear_dir('graphs')

    config_instance = CONFIG()
    with open('config.json', 'w') as f:
        json.dump(config_instance.__dict__, f, indent=4)
    with open('results.json', 'w') as f:
        json.dump(json_data, f, indent=4)
    with open('results.pkl', 'wb') as f:
        pickle.dump(json_data, f)
    visualize(json_data)


def setup_progressbars():
    '''
    Setup progress bars
    '''
    global pbar_txns, pbar_blocks
    pbar_txns = tqdm(desc='Txns: ', total=CONFIG.TOTAL_NUM_TRANSACTIONS,
                     position=0, leave=True)
    pbar_blocks = tqdm(
        desc='Blks: ', total=CONFIG.TOTAL_NUM_BLOCKS, position=1, leave=True)


def post_enqueue_hooks(event):
    global free_tnx_counter
    if event.type in [EventType.BLOCK_BROADCAST, EventType.BLOCK_MINE_FINISH, EventType.BLOCK_MINE_START]:
        free_tnx_counter = 0


def post_run_hooks(event):

    def update_progress_bars():
        global pbar_txns, pbar_blocks
        global free_tnx_counter, blocks_broadcasted
        if event.type == EventType.TXN_BROADCAST:
            free_tnx_counter += 1
            pbar_txns.update(1)
        elif event.type == EventType.BLOCK_BROADCAST:
            blocks_broadcasted += 1
            pbar_blocks.update(1)

    def termination_condition():
        global blocks_broadcasted
        if blocks_broadcasted > CONFIG.TOTAL_NUM_BLOCKS + 5:
            simulation.stop_sim = True

    def create_block_trigger():
        global free_tnx_counter
        if free_tnx_counter > (CONFIG.BLOCK_TXNS_TRIGGER_THRESHOLD*5):
            miner_peer = random.choice(peers_network)
            time_stamp = simulation.clock + 10
            new_block_event = Event(EventType.BLOCK_CREATE, time_stamp,
                                    time_stamp, miner_peer.block_chain.generate_block, (), f"{miner_peer} create_block")
            simulation.enqueue(new_block_event)
            free_tnx_counter = 0

    update_progress_bars()
    termination_condition()
    create_block_trigger()


def add_simulation_hooks(simulation):

    simulation.reg_hooks(HookType.POST_ENQUEUE, post_enqueue_hooks)
    simulation.reg_hooks(HookType.POST_RUN, post_run_hooks)


def main():
    global config_instance, peers_network, pbar_txns, pbar_blocks

    config_instance = CONFIG()

    print('Simulation parameters: ')
    for key, value in config_instance.__dict__.items():
        print(f"{key.rjust(35)}: {value}")

    peers_network = create_network(CONFIG.NUMBER_OF_PEERS)
    logger.info("Network created")
    print("Network created")

    log_peers(peers_network)
    schedule_transactions(peers_network)
    logger.info("Transactions scheduled")
    print("Transactions scheduled")

    logger.info("Simulation started")
    print("Simulation started")
    try:
        setup_progressbars()
        add_simulation_hooks(simulation)
        simulation.run()
        logger.info("Simulation ended")
    except KeyboardInterrupt:
        logger.info("Simulation interrupted")
    finally:
        pbar_txns.close()
        pbar_blocks.close()
        print("Simulation ended")

        export_data(peers_network)
        logger.info("Data exported")
        print("Data exported")


if __name__ == "__main__":
    main()
