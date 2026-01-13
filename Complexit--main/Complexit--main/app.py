from flask import Flask, render_template, request, redirect
import tree
import json
import os

app = Flask(__name__)

# =========================
# MÉMOIRE
# =========================
trees = {}
queue = []
current_root = None
current_name = None
current_n = 0
current_used = set()

DATA_FILE = "trees.json"


# =========================
# OUTILS ARBRE (first_child / next_sibling)
# =========================
def get_children(node):
    children = []
    c = node.first_child
    while c:
        children.append(c)
        c = c.next_sibling
    return children


def subtree_leaves_count(node):
    kids = get_children(node)
    if not kids:
        return 1
    return sum(subtree_leaves_count(k) for k in kids)


def layout_tree_svg(root, x_spacing=120, y_spacing=120, top_margin=60, left_margin=60):
    if root is None:
        return [], [], 500, 300

    node_id = 0
    ids = {}      # key = id(node) -> int
    widths = {}   # key = id(node) -> leaf count

    def assign_id(n):
        nonlocal node_id
        k = id(n)
        if k not in ids:
            ids[k] = node_id
            node_id += 1

    def compute_width(n):
        assign_id(n)
        widths[id(n)] = subtree_leaves_count(n)
        for ch in get_children(n):
            compute_width(ch)

    compute_width(root)

    nodes = []
    edges = []

    def place(n, x_start, depth):
        kids = get_children(n)
        y = top_margin + depth * y_spacing

        if not kids:
            x = left_margin + x_start * x_spacing
        else:
            cur = x_start
            child_centers = []
            for ch in kids:
                w = widths[id(ch)]
                cx = place(ch, cur, depth + 1)
                child_centers.append(cx)
                cur += w

            x = sum(child_centers) / len(child_centers)

            for cx in child_centers:
                cy = top_margin + (depth + 1) * y_spacing
                edges.append({"x1": x, "y1": y, "x2": cx, "y2": cy})

        nodes.append({"id": ids[id(n)], "label": n.value, "x": x, "y": y})
        return x

    place(root, 0, 0)

    max_x = max(n["x"] for n in nodes) if nodes else 500
    max_y = max(n["y"] for n in nodes) if nodes else 300
    svg_w = int(max_x + left_margin + 60)
    svg_h = int(max_y + top_margin + 120)

    return nodes, edges, svg_w, svg_h


# =========================
# PERSISTENCE (JSON)
# =========================
def node_to_dict(node):
    return {
        "value": node.value,
        "children": [node_to_dict(ch) for ch in get_children(node)]
    }


def dict_to_node(data):
    root = tree.Node(data["value"])
    prev = None
    for child_data in data.get("children", []):
        child_node = dict_to_node(child_data)
        if prev is None:
            root.first_child = child_node
        else:
            prev.next_sibling = child_node
        prev = child_node
    return root


def save_trees():
    payload = {name: node_to_dict(root) for name, root in trees.items()}
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_trees():
    global trees
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            payload = json.load(f)
        trees = {name: dict_to_node(data) for name, data in payload.items()}


# Charger au démarrage
load_trees()


# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/menu")
def menu():
    # envoie la liste des arbres enregistrés (optionnel)
    return render_template("menu.html", names=sorted(trees.keys()))


@app.route("/build", methods=["GET", "POST"])
def build():
    global queue, current_root, current_name, current_n, trees, current_used

    msg = ""

    if request.method == "POST":

        # Démarrage
        if "start" in request.form:
            current_name = request.form["name"].strip()
            current_n = int(request.form["n"])
            root_val = request.form["root"].strip()

            current_root = tree.Node(root_val)
            queue = [current_root]
            current_used = {root_val}

        # Ajouter fils
        elif "k" in request.form and queue:
            node = queue.pop(0)
            k = int(request.form["k"])
            k = max(0, min(k, current_n))

            for i in range(k):
                val = (request.form.get(f"child{i}") or "").strip()
                if not val:
                    continue

                if val in current_used:
                    msg = f"⚠️ La valeur '{val}' existe déjà. Choisis une autre valeur."
                    continue

                c = tree.add_child(node, val)
                queue.append(c)
                current_used.add(val)

    # FIN => enregistrer + afficher
    if not queue and current_root:
        trees[current_name] = current_root
        save_trees()  # ✅ sauvegarde dans trees.json

        final_tree = current_root

        # reset construction
        current_root = None
        current_name = None
        current_n = 0
        current_used = set()

        nodes, edges, w, h = layout_tree_svg(final_tree, x_spacing=140, y_spacing=140)
        return render_template("build_done.html", nodes=nodes, edges=edges, w=w, h=h)

    node = queue[0] if queue else None
    return render_template("build.html", node=node, n=current_n, msg=msg, used=list(current_used))


@app.route("/show_graph", methods=["GET", "POST"])
def show_graph():
    if request.method == "POST":
        name = request.form["name"].strip()
        t = trees.get(name)

        if not t:
            return "❌ Arbre non trouvé<br><a href='/menu'>Retour</a>"

        nodes, edges, w, h = layout_tree_svg(t, x_spacing=140, y_spacing=140)
        return render_template("show_graph.html", nodes=nodes, edges=edges, w=w, h=h, name=name)

    # GET : afficher la liste des arbres enregistrés
    return render_template("select_tree.html", names=sorted(trees.keys()))


@app.route("/delete_tree", methods=["POST"])
def delete_tree():
    """Optionnel: supprimer un arbre enregistré."""
    name = request.form.get("name", "").strip()
    if name in trees:
        del trees[name]
        save_trees()
    return redirect("/menu")


if __name__ == "__main__":
    app.run(debug=True)
