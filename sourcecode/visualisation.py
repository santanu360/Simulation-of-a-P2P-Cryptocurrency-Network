import pickle
import pygraphviz as pgv
from matplotlib import pyplot as plt

from utils import create_directory


def block_chain_visualization(results):
    num_peers = len(results['peers'])
    Graph = pgv.AGraph(strict=True, directed=True, rankdir="LR")
    Graph.node_attr["shape"] = "record"
    for peer in results['peers']:
        block_chain = peer['block_chain']
        peer_id = peer['id']
        G = Graph.add_subgraph(
            name=f"cluster_{peer_id}", label=f"Peer {peer_id}")
        G.graph_attr["label"] = f"Peer {peer_id} description: {peer['cpu_net_description']} [ratio:{peer['longest_chain_contribution']}]"

        for block in block_chain['blocks']:
            label = f' {{ id:{block["block_id"]} | miner:{block["miner"]} }} |'
            label = label + \
                f'{{ #tx: {block["num_txns"]} | ts: {round(block["timestamp"],2)} }}'
            if block['block_id'] != 'gen_blk':
                label = label + \
                    f' | {{ <prev> prev: {block["prev_block"]["hash"][:8]}'
            else:
                label = label + f' | {{ <prev> prev: None'
            label = label + f' | <self> self: {block["self_hash"][:8]} }}'
            if block['self'] in block_chain['longest_chain']:
                G.add_node(peer_id + block['block_id'],
                           color="green", label=label)
            elif block['block_id'] == 'gen_blk':
                G.add_node(peer_id + block['block_id'],
                           color="blue", label=label)
            else:
                G.add_node(peer_id + block['block_id'], label=label)
        for block in block_chain['blocks']:
            if block['prev_block'] == '':
                continue
            prev_block = block['prev_block']
            if block['self'] in block_chain['longest_chain']:
                G.add_edge(
                    peer_id+prev_block['id'], peer_id + block['block_id'],  tailport="self", headport="prev", dir="back", color="green")
            else:
                G.add_edge(peer_id+prev_block['id'], peer_id + block['block_id'],
                           tailport="self", headport="prev", dir="back")
    Graph.draw(f"graphs/graphs.pdf", prog="dot")


def fraction_vs_hashpower_visualization(results):

    total_blocks = len(results["peers"][0]["block_chain"]["blocks"])
    longest_chain = results["peers"][0]["block_chain"]["longest_chain_length"]
    longest_chain_div_total_blocks = longest_chain/total_blocks
    ratios = results['ratios']

    with open('graphs/sim_results.txt', 'w') as fileobj:
        fileobj.write(f"Total blocks: {total_blocks}\n")
        fileobj.write(f"Longest chain: {longest_chain}\n")
        fileobj.write(
            f"Longest chain/Total blocks: {longest_chain_div_total_blocks}\n")
        fileobj.write('\n\n')
        fileobj.write(
            'PeerID \t\t Hashing power \t\t Network speed \t\t Number of peers \t\t Ratio\n')
        fileobj.write(
            f"low  \t\t\t low \t\t\t [todo] \t\t\t {ratios['cpu_low']['net_low']}% \n")
        fileobj.write(
            f"low  \t\t\t high \t\t\t [todo] \t\t\t {ratios['cpu_low']['net_high']}% \n")
        fileobj.write(
            f"high \t\t\t low \t\t\t [todo] \t\t\t {ratios['cpu_high']['net_low']}% \n")
        fileobj.write(
            f"high \t\t\t high \t\t\t [todo] \t\t\t {ratios['cpu_high']['net_high']}% \n")

    plt.figure(figsize=(10, 6))

    data_points = []
    for peer in results['peers']:
        data_points.append({
            'contrib': peer['longest_chain_contribution'],
            'net': peer['is_slow_network'],
            'hash_power': peer['cpu_power'],
            'peer': peer['id']
        })
    data_points = sorted(data_points, key=lambda x: x['hash_power'])

    hash_powers = list(map(lambda x: x['hash_power']*100, data_points))
    peer_ids = list(map(lambda x: x['peer'], data_points))

    contribs_slow = list(map(lambda x: x['contrib'], filter(
        lambda x: x['net'] == True, data_points)))
    contribs_slow_ids = list(map(lambda x: x['peer'], filter(
        lambda x: x['net'] == True, data_points)))

    contribs_fast = list(map(lambda x: x['contrib'], filter(
        lambda x: x['net'] == False, data_points)))
    contribs_fast_ids = list(map(lambda x: x['peer'], filter(
        lambda x: x['net'] == False, data_points)))

    # Plot the scatter
    # plt.plot(fraction_of_hash_power, peer_id, label='Slow Peer', color='blue')
    plt.plot(peer_ids, hash_powers, label='Fraction of Hash Power (%)',
             linestyle='--', color='green')
    plt.scatter(contribs_slow_ids, contribs_slow,
                label='Fraction of blocks Slow Peer (%)', color='blue')
    plt.scatter(contribs_fast_ids, contribs_fast,
                label='Fraction of blocks Fast Peer (%)', color='red')

    # Add labels and title
    plt.xlabel('Peer ID')
    plt.ylabel('Fraction of Blocks in Longest Chain (%)')
    plt.title('Fraction of Blocks in Longest Chain vs. Peer ID')

    # Add legend
    plt.legend()

    # Show the plot
    plt.grid(True)
    plt.savefig('graphs/fraction_vs_hashpower.jpeg')


def forks_branches_visualization(results):
    group_gap = 0.2
    bar_width = 0.2
    bar_gap = 0.05

    fork_bar_values = []
    fork_bar_positions = []

    branch_bar_values = []
    branch_bar_positions = []

    datas = []
    for peer in results['summary']:
        peer_id = peer['peer']
        start_index = peer_id.find("=") + 1
        end_index = peer_id.find(")")
        peer_id = peer_id[start_index:end_index]
        forks = list(map(lambda x: x["num_forks"], peer['forks']))
        branches = list(map(lambda x: x["length"], peer['branches']))
        datas.append({
            'peer': peer_id,
            'forks': forks,
            'branches': branches
        })

    pos = 0
    label_values = []
    label_positions = []
    for data in datas:
        peer, forks, branches = data['peer'], data['forks'], data['branches']
        group_start = pos
        for data_item in forks:
            fork_bar_values.append(data_item)
            fork_bar_positions.append(pos)
            pos = pos + bar_width+bar_gap
        label_values.append(peer)
        label_positions.append((pos+group_start-bar_width-bar_gap) / 2)
        pos = pos + group_gap

    fig, axs = plt.subplots(2, 1, figsize=(pos, 8))

    axs[0].bar(fork_bar_positions, fork_bar_values, width=bar_width,
               label='Forks', color='royalblue')
    axs[0].set_xticks(label_positions, label_values)
    axs[0].set_xlabel('Peers')
    axs[0].set_ylabel('Number of Forks')
    axs[0].set_title('Forks per Peer')
    axs[0].legend()
    axs[0].grid(True)

    pos = 0
    label_values = []
    label_positions = []
    for data in datas:
        peer, forks, branches = data['peer'], data['forks'], data['branches']
        group_start = pos
        for data_item in branches:
            branch_bar_values.append(data_item)
            branch_bar_positions.append(pos)
            pos = pos + bar_width+bar_gap
        label_values.append(peer)
        label_positions.append((pos+group_start-bar_width-bar_gap) / 2)
        pos = pos + group_gap

    axs[1].bar(branch_bar_positions, branch_bar_values, width=bar_width,
               label='Branches', color='darkorange')
    axs[1].set_xticks(label_positions, label_values)
    axs[1].set_xlabel('Peers')
    axs[1].set_ylabel('Number of Branches')
    axs[1].set_title('Branches per Peer')
    axs[1].legend()
    axs[1].grid(True)

    plt.tight_layout()
    plt.savefig('graphs/forks_branches.jpeg')


def visualize(results):
    create_directory('graphs')

    block_chain_visualization(results)
    fraction_vs_hashpower_visualization(results)
    forks_branches_visualization(results)


if __name__ == '__main__':
    results = ''
    with open('results.pkl', 'rb') as fileobj:
        results = pickle.load(fileobj)

    visualize(results=results)
