import json
import sys

path = sys.argv[1]  # input("Enter the path to the results.json file: ")

results = []
with open(f'{path}/results.json') as data_file:
    results = json.load(data_file)

for peer in results['peers']:
    peer.pop('neighbours')
    for block in peer['block_chain']['blocks']:
        block.pop('transactions')

with open(f'{path}/results_filtered.json', 'w') as outfile:
    json.dump(results, outfile, indent=4)
