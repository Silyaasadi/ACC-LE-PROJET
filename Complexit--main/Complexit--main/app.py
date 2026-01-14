from flask import Flask, render_template, request, redirect
import tree
import json
import os
from collections import deque

app = Flask(__name__)

# =========================
# MÉMOIRE
# =========================
trees = {}
tree_orders = {}
queue = []
current_root = None
current_name = None
current_n = 0
current_used = set()

DATA_FILE = "trees.json"

# =========================
# OUTILS ARBRE
# =========================
def get_children(node):
    res = []
    c = node.first_child
    while c:
        res.append(c)
        c = c.next_sibling
    return res

def subtree_leaves_count(node):
    kids = get_children(node)
    if not kids:
        return 1
    return sum(subtree_leaves_count(k) for k in kids)

# =========================
# LAYOUT GRAPH
# =========================
def layout_tree_svg(root, order=None, x_spacing=120, y_spacing=120, top_margin=60, left_margin=60):
    if root is None:
        return [], [], 500, 300

    node_id = 0
    ids = {}
    widths = {}

    def assign_id(n):
        nonlocal node_id
        if id(n) not in ids:
            ids[id(n)] = node_id
            node_id += 1

    def compute_width(n):
        assign_id(n)
        widths[id(n)] = subtree_leaves_count(n)
        for ch in get_children(n):
            compute_width(ch)

    compute_width(root)
    nodes, edges = [], []

    def place(n, x_start, depth):
        kids = get_children(n)
        y = top_margin + depth * y_spacing

        if not kids:
            x = left_margin + x_start * x_spacing
        else:
            cur = x_start
            centers = []
            for ch in kids:
                w = widths[id(ch)]
                cx = place(ch, cur, depth + 1)
                centers.append(cx)
                cur += w
            x = sum(centers) / len(centers)
            for cx in centers:
                cy = top_margin + (depth + 1) * y_spacing
                edges.append({"x1": x, "y1": y, "x2": cx, "y2": cy})

        pos = order.index(n.value) + 1 if order and n.value in order else 0
        nodes.append({"id": ids[id(n)], "label": n.value, "x": x, "y": y, "pos": pos})
        return x

    place(root, 0, 0)
    max_x = max(n["x"] for n in nodes)
    max_y = max(n["y"] for n in nodes)
    return nodes, edges, int(max_x + 150), int(max_y + 200)

# =========================
# JSON
# =========================
def node_to_dict(node):
    return {"value": node.value, "children": [node_to_dict(c) for c in get_children(node)]}

def dict_to_node(data):
    root = tree.Node(data["value"])
    prev = None
    for cd in data.get("children", []):
        c = dict_to_node(cd)
        if prev is None:
            root.first_child = c
        else:
            prev.next_sibling = c
        prev = c
    return root

def save_trees():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({
            name: {
                "order": tree_orders[name],
                "tree": node_to_dict(trees[name])
            } for name in trees
        }, f, ensure_ascii=False, indent=2)


def load_trees():
    global trees, tree_orders
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
            for name, data in raw.items():
                trees[name] = dict_to_node(data["tree"])
                tree_orders[name] = data["order"]


load_trees()

# =========================
# ROUTES
# =========================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/menu")
def menu():
    return render_template("menu.html", names=sorted(trees.keys()))

@app.route("/build", methods=["GET", "POST"])
def build():
    global queue, current_root, current_name, current_n, current_used

    msg = ""
    if request.method == "POST":
        if "start" in request.form:
            current_name = request.form["name"].strip()
            current_n = int(request.form["n"])
            current_root = tree.Node(request.form["root"].strip())
            queue = [current_root]
            current_used = {current_root.value}

        elif "k" in request.form and queue:
            node = queue.pop(0)
            k = min(int(request.form["k"]), current_n)
            for i in range(k):
                v = request.form.get(f"child{i}", "").strip()
                if v and v not in current_used:
                    c = tree.add_child(node, v)
                    queue.append(c)
                    current_used.add(v)

    if not queue and current_root:
        trees[current_name] = current_root
        tree_orders[current_name] = current_n

        save_trees()
        nodes, edges, w, h = layout_tree_svg(current_root)
        current_root = None
        return render_template("build_done.html", nodes=nodes, edges=edges, w=w, h=h)

    return render_template("build.html", node=queue[0] if queue else None, n=current_n, msg=msg)







def height_of_tree(node):
    if node is None:
        return 0
    kids = get_children(node)
    if not kids:
        return 1
    return 1 + max(height_of_tree(ch) for ch in kids)

@app.route("/height", methods=["GET", "POST"])
def height_page():
    if request.method == "GET":
       return render_template("height_list.html", names=sorted(trees.keys()), msg=None)

    name = request.form.get("name", "").strip()
    t = trees.get(name)

    if not t:
      return render_template("height_list.html", names=sorted(trees.keys()), msg="❌ Arbre non trouvé.")

    h = height_of_tree(t)
    return render_template("height_result.html", name=name, height=h)









@app.route("/show_graph", methods=["GET", "POST"])
def show_graph():
    if request.method == "POST":
        t = trees.get(request.form["name"])
        nodes, edges, w, h = layout_tree_svg(t)
        return render_template("show_graph.html", nodes=nodes, edges=edges, w=w, h=h, name="Arbre")
    return render_template("select_tree.html", names=sorted(trees.keys()))

@app.route("/show_graph_traversal", methods=["POST"])
def show_graph_traversal():
    name = request.form["name"]
    mode = request.form["mode"]
    t = trees.get(name)

    if mode == "bfs":
        order = tree.bfs(t)
        title = "Parcours en largeur"
    else:
        order = tree.dfs(t)
        title = "Parcours en profondeur"

    nodes, edges, w, h = layout_tree_svg(t, order=order)
    return render_template("show_graph.html", nodes=nodes, edges=edges, w=w, h=h, name=title)
@app.route("/show_traversal_text", methods=["POST"])
def show_traversal_text():
    name = request.form["name"]
    mode = request.form["mode"]
    t = trees.get(name)

    if mode == "bfs":
        order = tree.bfs(t)
        title = "Parcours en largeur (texte)"
    else:
        order = tree.dfs(t)
        title = "Parcours en profondeur (texte)"

    return render_template("show_traversal_text.html", name=name, title=title, order=order)
@app.route("/insert", methods=["GET","POST"])
def insert_node():
    msg = ""
    nodes = edges = None
    w = h = 0

    if request.method == "POST":

        # ========== INSERT ==========
        if "parent" in request.form:
            name = request.form["name"]
            parent = request.form["parent"]
            new = request.form["new"]

            t = trees.get(name)
            ordre = tree_orders.get(name, 0)

            if t:
                ok, msg = tree.insert(t, parent, new, ordre)
                if ok:
                    save_trees()

        # ========== AFFICHER ==========
        elif "show" in request.form:
            name = request.form["name"]
            t = trees.get(name)
            if t:
                nodes, edges, w, h = layout_tree_svg(t)

    return render_template(
        "insert.html",
        names=sorted(trees.keys()),
        msg=msg,
        nodes=nodes,
        edges=edges,
        w=w,
        h=h
    )




def node_address(root, target):
    """Retourne l'adresse 'R.0.1...' du node target, ou None."""
    if root is None or target is None:
        return None
    if root is target:
        return "R"

    stack = [(root, "R")]
    while stack:
        node, addr = stack.pop()
        kids = get_children(node)
        for i, ch in enumerate(kids):
            ch_addr = f"{addr}.{i}"
            if ch is target:
                return ch_addr
            stack.append((ch, ch_addr))
    return None


def get_node_by_address(root, addr):
    """Convertit une adresse 'R.0.1' en node."""
    if root is None:
        return None
    addr = (addr or "").strip()
    if addr == "R":
        return root
    if not addr.startswith("R."):
        return None

    parts = addr.split(".")[1:]  # enlève R
    cur = root
    for p in parts:
        if not p.isdigit():
            return None
        idx = int(p)
        kids = get_children(cur)
        if idx < 0 or idx >= len(kids):
            return None
        cur = kids[idx]
    return cur


def find_node_by_value(root, value):
    """Trouve le node par valeur (unique), ou None."""
    if root is None:
        return None
    value = (value or "").strip()
    if not value:
        return None

    stack = [root]
    while stack:
        node = stack.pop()
        if node.value == value:
            return node
        for ch in get_children(node):
            stack.append(ch)
    return None


def build_parent_map(root):
    """Retourne parent[node] = parent_node (root -> None)."""
    parent = {}
    if root is None:
        return parent
    parent[root] = None
    q = [root]
    while q:
        node = q.pop(0)
        for ch in get_children(node):
            parent[ch] = node
            q.append(ch)
    return parent


def path_nodes_between(root, a_node, b_node):
    """Retourne la liste des nodes sur le chemin a -> b (inclut a et b)."""
    if root is None or a_node is None or b_node is None:
        return None

    parent = build_parent_map(root)

    # Ancêtres de a
    ancestors = set()
    x = a_node
    while x is not None:
        ancestors.add(x)
        x = parent.get(x)

    # Trouver LCA en remontant depuis b
    lca = b_node
    while lca is not None and lca not in ancestors:
        lca = parent.get(lca)
    if lca is None:
        return None  # pas dans le même arbre

    # Chemin a -> lca
    up = []
    x = a_node
    while x is not lca:
        up.append(x)
        x = parent.get(x)
    up.append(lca)

    # Chemin lca -> b (descendant)
    down = []
    x = b_node
    while x is not lca:
        down.append(x)
        x = parent.get(x)
    down.reverse()

    return up + down

@app.route("/search")
def search_home():
    return render_template("search_home.html")

@app.route("/search_word", methods=["GET", "POST"])
def search_word():
    if request.method == "GET":
        return render_template("search_word.html",
                               names=sorted(trees.keys()),
                               selected_tree=None,
                               msg=None,
                               result=None)

    tree_name = request.form["tree_name"].strip()
    value = request.form["value"].strip()
    t = trees.get(tree_name)

    if not t:
        return render_template("search_word.html",
                               names=sorted(trees.keys()),
                               selected_tree=tree_name,
                               msg="❌ Arbre non trouvé.",
                               result=None)

    if len(value) > 20:
        return render_template("search_word.html",
                               names=sorted(trees.keys()),
                               selected_tree=tree_name,
                               msg="⚠️ Mot trop long (≤ 20).",
                               result=None)

    node = find_node_by_value(t, value)
    if not node:
        return render_template("search_word.html",
                               names=sorted(trees.keys()),
                               selected_tree=tree_name,
                               msg=f"❌ '{value}' introuvable.",
                               result=None)

    addr = node_address(t, node)
    return render_template("search_word.html",
                           names=sorted(trees.keys()),
                           selected_tree=tree_name,
                           msg="✅ Trouvé.",
                           result={"value": value, "addr": addr})


@app.route("/search_path", methods=["GET", "POST"])
def search_path():
    if request.method == "GET":
        return render_template("search_path.html",
                               names=sorted(trees.keys()),
                               selected_tree=None,
                               msg=None,
                               path=None,
                               tree=None)

    tree_name = request.form["tree_name"].strip()
    a_val = request.form["a_val"].strip()
    b_val = request.form["b_val"].strip()
    t = trees.get(tree_name)

    if not t:
        return render_template("search_path.html",
                               names=sorted(trees.keys()),
                               selected_tree=tree_name,
                               msg="❌ Arbre non trouvé.",
                               path=None,
                               tree=None)

    a = find_node_by_value(t, a_val)
    b = find_node_by_value(t, b_val)

    if not a or not b:
        return render_template("search_path.html",
                               names=sorted(trees.keys()),
                               selected_tree=tree_name,
                               msg="❌ 'a' ou 'b' introuvable dans l’arbre.",
                               path=None,
                               tree=tree_name)

    nodes_path = path_nodes_between(t, a, b)
    if not nodes_path:
        return render_template("search_path.html",
                               names=sorted(trees.keys()),
                               selected_tree=tree_name,
                               msg="❌ Impossible de calculer le chemin.",
                               path=None,
                               tree=tree_name)

    path = [{"value": nd.value, "addr": node_address(t, nd)} for nd in nodes_path]
    return render_template("search_path.html",
                           names=sorted(trees.keys()),
                           selected_tree=tree_name,
                           msg="✅ Chemin trouvé.",
                           path=path,
                           tree=tree_name)






def find_parent_and_node(root, value):
    """Retourne (parent, node) du node dont node.value == value. parent=None si root."""
    if root is None:
        return (None, None)
    if root.value == value:
        return (None, root)

    stack = [root]
    while stack:
        node = stack.pop()
        for ch in get_children(node):
            if ch.value == value:
                return (node, ch)
            stack.append(ch)
    return (None, None)

def delete_node_by_value(root, value):
    """
    Supprime le nœud ayant 'value' et TOUT son sous-arbre.
    Retourne (new_root, ok, msg)
    """
    if root is None:
        return (None, False, "❌ Arbre vide.")

    parent, node = find_parent_and_node(root, value)
    if node is None:
        return (root, False, "❌ Nœud introuvable.")

    # Cas 1 : supprimer la racine
    if parent is None:
        return (None, True, "✅ Racine supprimée (arbre supprimé).")

    # Cas 2 : supprimer un enfant (node) du parent dans la liste first_child/next_sibling
    prev = None
    cur = parent.first_child
    while cur and cur is not node:
        prev = cur
        cur = cur.next_sibling

    if cur is None:
        return (root, False, "❌ Erreur suppression (lien introuvable).")

    # Retirer node de la chaîne des frères
    if prev is None:
        parent.first_child = node.next_sibling
    else:
        prev.next_sibling = node.next_sibling

    # Optionnel: couper pour aider le GC
    node.next_sibling = None

    return (root, True, "✅ Nœud supprimé (sous-arbre supprimé).")






@app.route("/edit", methods=["GET", "POST"])
def edit_node():
    msg = None
    if request.method == "GET":
        return render_template("edit.html", names=sorted(trees.keys()),
                               selected_tree=None, msg=None)

    tree_name = request.form.get("tree_name", "").strip()
    old_val = request.form.get("old_val", "").strip()
    new_val = request.form.get("new_val", "").strip()

    t = trees.get(tree_name)
    if not t:
        return render_template("edit.html", names=sorted(trees.keys()),
                               selected_tree=tree_name, msg="❌ Arbre non trouvé.")

    if not old_val or not new_val:
        return render_template("edit.html", names=sorted(trees.keys()),
                               selected_tree=tree_name, msg="⚠️ Champs vides.")

    node = find_node_by_value(t, old_val)
    if not node:
        return render_template("edit.html", names=sorted(trees.keys()),
                               selected_tree=tree_name, msg="❌ Nœud introuvable.")

    # Empêcher doublon (valeurs uniques)
    already = find_node_by_value(t, new_val)
    if already and already is not node:
        return render_template("edit.html", names=sorted(trees.keys()),
                               selected_tree=tree_name, msg="❌ Nouvelle valeur déjà utilisée.")

    node.value = new_val
    save_trees()
    return render_template("edit.html", names=sorted(trees.keys()),
                           selected_tree=tree_name, msg="✅ Nœud modifié avec succès.")





def delete_node_keep_children(root, value):
    parent, node = find_parent_and_node(root, value)
    if node is None:
        return root, False, "❌ Nœud introuvable."
    if parent is None:
        return root, False, "⚠️ Suppression racine: à gérer séparément."

    # trouver node dans la chaîne des enfants du parent
    prev = None
    cur = parent.first_child
    while cur and cur is not node:
        prev = cur
        cur = cur.next_sibling
    if cur is None:
        return root, False, "❌ Lien introuvable."

    kids = get_children(node)         # enfants de a
    after = node.next_sibling         # frère suivant de a

    if not kids:
        # a n'a pas d'enfants -> on saute a
        if prev is None:
            parent.first_child = after
        else:
            prev.next_sibling = after
    else:
        # a a des enfants -> ils prennent sa place
        first_kid = kids[0]

        if prev is None:
            parent.first_child = first_kid
        else:
            prev.next_sibling = first_kid

        # relier le dernier enfant au "after"
        last = first_kid
        while last.next_sibling:
            last = last.next_sibling
        last.next_sibling = after

    # détacher a
    node.first_child = None
    node.next_sibling = None

    return root, True, "✅ Nœud supprimé, liens refaits."

@app.route("/delete", methods=["GET", "POST"])
def delete_node():
    if request.method == "GET":
        return render_template(
            "delete.html",
            names=sorted(trees.keys()),
            selected_tree=None,
            msg=None
        )

    tree_name = request.form.get("tree_name", "").strip()
    value = request.form.get("value", "").strip()

    t = trees.get(tree_name)
    if not t:
        return render_template(
            "delete.html",
            names=sorted(trees.keys()),
            selected_tree=tree_name,
            msg="❌ Arbre non trouvé."
        )

    # ✅ suppression du nœud seulement (on garde les enfants)
    new_root, ok, msg = delete_node_keep_children(t, value)

    if ok:
        trees[tree_name] = new_root
        save_trees()

    return render_template(
        "delete.html",
        names=sorted(trees.keys()),
        selected_tree=tree_name,
        msg=msg
    )





if __name__ == "__main__":
    app.run(debug=True)
