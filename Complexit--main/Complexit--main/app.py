from flask import Flask, render_template, request
import tree

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


# =========================
# OUTILS ARBRE
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
    """
    Layout SAFE : utilise id(node) comme clé (évite erreurs unhashable).
    Retour: nodes, edges, w, h
    """
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
# ROUTES
# =========================
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/menu")
def menu():
    return render_template("menu.html")


@app.route("/build", methods=["GET", "POST"])
def build():
    global queue, current_root, current_name, current_n, trees, current_used

    msg = ""

    if request.method == "POST":

        # 1) Démarrer un nouvel arbre
        if "start" in request.form:
            current_name = request.form["name"].strip()
            current_n = int(request.form["n"])
            root_val = request.form["root"].strip()

            current_root = tree.Node(root_val)
            queue = [current_root]
            current_used = {root_val}

        # 2) Ajouter les fils (BFS)
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

    # ✅ FIN : afficher l'arbre complet en graphe
    if not queue and current_root:
        trees[current_name] = current_root
        final_tree = current_root

        # reset état de construction (l'arbre reste enregistré)
        current_root = None
        current_name = None
        current_n = 0
        current_used = set()

        nodes, edges, w, h = layout_tree_svg(final_tree)
        return render_template("build_done.html", nodes=nodes, edges=edges, w=w, h=h)

    node = queue[0] if queue else None
    return render_template("build.html", node=node, n=current_n, msg=msg, used=list(current_used))


@app.route("/show_graph", methods=["GET", "POST"])
def show_graph():
    if request.method == "POST":
        name = request.form["name"]
        t = trees.get(name)
        if not t:
            return "❌ Arbre non trouvé<br><a href='/menu'>Retour</a>"

        nodes, edges, w, h = layout_tree_svg(t)
        return render_template("show_graph.html", nodes=nodes, edges=edges, w=w, h=h, name=name)

    return render_template("show_graph.html")


if __name__ == "__main__":
    app.run(debug=True)
