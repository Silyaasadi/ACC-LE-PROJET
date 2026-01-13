class Node:
    def __init__(self, value):
        self.value = value
        self.first_child = None
        self.next_sibling = None


def add_child(parent, value):
    new = Node(value)
    if parent.first_child is None:
        parent.first_child = new
    else:
        cur = parent.first_child
        while cur.next_sibling:
            cur = cur.next_sibling
        cur.next_sibling = new
    return new


def build_manual(root_value, n, input_func):
    root = Node(root_value)
    q = [root]

    while q:
        parent = q.pop(0)

        for i in range(n):
            name = input_func(f"Fils {i+1} de {parent.value} (ou NULL): ")

            if name.upper() == "NULL":
                break

            child = add_child(parent, name)
            q.append(child)

    return root


def height(node):
    if node is None:
        return -1
    m = -1
    c = node.first_child
    while c:
        m = max(m, height(c))
        c = c.next_sibling
    return m + 1


def search(node, value):
    if node is None:
        return None
    if node.value == value:
        return node
    c = node.first_child
    while c:
        r = search(c, value)
        if r:
            return r
        c = c.next_sibling
    return None
