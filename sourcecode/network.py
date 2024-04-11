import random
from Peer import Peer
from Link import Link
from config import CONFIG


def is_connected(peers: list[Peer]):
    """
    Returns True if all peers are connected to each other, False otherwise.
    """
    is_visited = {}
    cur_peer = peers[0]
    queue = [cur_peer]
    is_visited[cur_peer.id] = True
    while queue:
        cur_peer = queue.pop(0)
        is_visited[cur_peer.id] = True
        for peer in cur_peer.neighbours.keys():
            if peer.id not in is_visited:
                queue.append(peer)
    return all(is_visited)


def draw_graph(peers):
    """
    Draws a graph of the peers and their connections.
    """
    import networkx as nx
    import matplotlib.pyplot as plt
    G = nx.Graph()
    for peer in peers:
        G.add_node(peer.id)
        for connected_peer in peer.connected_peers:
            G.add_edge(peer.id, connected_peer.id)
    nx.draw(G, with_labels=True)
    plt.show()


def create_network(n: int) -> list[Peer]:
    is_slow_nets = [False] * n
    is_slow_cpus = [False] * n
    for i in random.sample(list(range(n)), round(n*CONFIG.Z0)):
        is_slow_nets[i] = True
    for i in random.sample(list(range(n)), round(n*CONFIG.Z1)):
        is_slow_cpus[i] = True

    peers = [Peer(id=i, is_slow_network=is_slow_nets[i], is_slow_cpu=is_slow_cpus[i])
             for i in range(n)]

    for peer in peers:
        peer.init_blockchain(peers=peers)

    for peer in peers:
        # choose random number of neighbours
        num_neighbours = random.randint(4, 6)
        # num_neighbours = random.randint(2, 3)
        random_neighbours = random.sample(
            peers, num_neighbours)  # choose random neighbours
        for neighbour in random_neighbours:
            if neighbour != peer:  # don't add yourself as a neighbour
                link = Link(peer, neighbour)
                # add neighbour to peer
                peer.connect(peer=neighbour, link=link)
                # add peer to neighbour
                neighbour.connect(peer=peer, link=link)
    if is_connected(peers):
        return peers
    else:
        return create_network(n)
