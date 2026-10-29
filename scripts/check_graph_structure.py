import csv
import networkx as nx

# 1. Load the frozen graph
G = nx.Graph()

with open("data/processed/nodes.csv", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        G.add_node(row["concept"])

with open("data/processed/edges.csv", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        G.add_edge(row["source"], row["target"])

# 2. Basic statistics
N = G.number_of_nodes()
M = G.number_of_edges()
degrees = dict(G.degree())

leaves = sum(d == 1 for d in degrees.values())
bridges = list(nx.bridges(G))
components = list(nx.connected_components(G))
lcc = max(map(len, components))

print("=== Basic Structure ===")
print("Nodes:", N)
print("Edges:", M)
print("Average degree:", round(2 * M / N, 3))
print("Density:", round(nx.density(G), 5))
print("Components:", len(components))
print("LCC ratio:", round(lcc / N, 4))

print("\n=== Structural Quality ===")
print("Leaf ratio:", round(leaves / N, 4))
print("Bridge ratio:", round(len(bridges) / M, 4))
print("Average clustering:", round(nx.average_clustering(G), 4))

print("\n=== Top 10 Degree Nodes ===")
for node, degree in sorted(
    degrees.items(), key=lambda x: -x[1]
)[:10]:
    print(node, degree)

# 3. Remove the highest-degree node
hub = max(degrees, key=degrees.get)
H = G.copy()
H.remove_node(hub)

new_lcc = max(map(len, nx.connected_components(H)))

print("\n=== Hub Removal Test ===")
print("Removed node:", hub)
print("LCC ratio after removal:", round(new_lcc / (N - 1), 4))
print("Components after removal:", nx.number_connected_components(H))

# 4. Shortest-path structure
distances = dict(nx.all_pairs_shortest_path_length(G, cutoff=3))
distance_2 = 0
distance_3 = 0

for source, targets in distances.items():
    for target, distance in targets.items():
        if source < target:
            if distance == 2:
                distance_2 += 1
            elif distance == 3:
                distance_3 += 1

print("\n=== Query Feasibility ===")
print("Distance-2 pairs:", distance_2)
print("Distance-3 pairs:", distance_3)