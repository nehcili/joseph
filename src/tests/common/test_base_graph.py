import pytest
from unittest.mock import patch
from src.common.base_graph import Node
from src.common.base_graph import Graph, Node

# Patch get_all_args for testing since it's imported in Node

# Import Node from the module under test

# Dummy get_all_args for Node._set_data
def dummy_get_all_args(*args, **kwargs):
    return {"args": args, "kwargs": kwargs}

class DummyNode(Node):
    def __init__(self, value=None, *args, **kwargs):
        self.value = value
        super().__init__(*args, **kwargs)

    def _forward(self, *args, **kwargs):
        # For leaf: return self.value; for non-leaf: sum all args
        if self.children is None:
            return self.value
        total = 0
        for a in args:
            if isinstance(a, (list, tuple)):
                total += sum(a)
            elif isinstance(a, dict):
                total += sum(a.values())
            else:
                total += a
        for v in kwargs.values():
            if isinstance(v, (list, tuple)):
                total += sum(v)
            elif isinstance(v, dict):
                total += sum(v.values())
            else:
                total += v
        return total

    def _backward(self, *args, depth=0, parent=None, _state=None, **kwargs):
        # Just record depth and parent in state
        state = dict(_state) if _state else {}
        state['depth'] = depth
        state['parent'] = parent
        return state

def test_node_call_sets_children():
    n1 = DummyNode(1)
    n2 = DummyNode(2)
    n3 = DummyNode(3)
    parent = DummyNode()
    parent(n1, n2, extra=n3)
    args_children, kwargs_children = parent.children
    assert args_children == [n1, n2]
    assert kwargs_children == {"extra": n3}

def test_node_call_accepts_collections():
    n1 = DummyNode(1)
    n2 = DummyNode(2)
    n3 = DummyNode(3)
    n4 = DummyNode(4)
    parent = DummyNode()
    parent([n1, n2], group={"a": n3, "b": n4})
    args_children, kwargs_children = parent.children
    assert args_children == [[n1, n2]]
    assert kwargs_children == {"group": {"a": n3, "b": n4}}

def test_node_call_invalid_type_raises():
    n = DummyNode()
    with pytest.raises(ValueError):
        n(123)  # Not a Node or collection of Nodes

def test_forward_leaf_node():
    n = DummyNode(42)
    assert n.forward() == 42

def test_forward_simple_graph():
    n1 = DummyNode(1)
    n2 = DummyNode(2)
    n3 = DummyNode(3)
    parent = DummyNode()
    parent(n1, n2, extra=n3)
    # Should sum all leaf values: 1 + 2 + 3 = 6
    assert parent.forward() == 6

def test_forward_nested_graph():
    n1 = DummyNode(1)
    n2 = DummyNode(2)
    n3 = DummyNode(3)
    mid = DummyNode()
    mid(n1, n2)
    root = DummyNode()
    root(mid, n3)
    # mid: 1+2=3, root: 3+3=6
    assert root.forward() == 6

def test_forward_with_collections():
    n1 = DummyNode(1)
    n2 = DummyNode(2)
    n3 = DummyNode(3)
    n4 = DummyNode(4)
    parent = DummyNode()
    parent([n1, n2], group={"a": n3, "b": n4})
    # [1,2] -> 1+2=3, group: {"a":3,"b":4} -> 3+4=7, total=3+7=10
    assert parent.forward() == 10

def test_backward_leaf_node():
    n = DummyNode(42)
    result = n.backward(depth=1, parent="root")
    assert isinstance(result, DummyNode)

def test_backward_simple_graph():
    n1 = DummyNode(1)
    n2 = DummyNode(2)
    parent = DummyNode()
    parent(n1, n2)
    result = parent.backward(depth=0, parent=None)
    assert isinstance(result, DummyNode)

def test_backward_nested_graph_state_propagation():
    n1 = DummyNode(1)
    n2 = DummyNode(2)
    mid = DummyNode()
    mid(n1)
    root = DummyNode()
    root(mid, n2)
    # Should not raise and should return root
    result = root.backward(depth=0, parent=None)
    assert result is root


class DummyGraph(Graph):
    def graph(self, *args, **kwargs):
        # Simple graph: two leaves and a parent node
        n1 = DummyNode(1)
        n2 = DummyNode(2)
        parent = DummyNode()
        parent(n1, n2)
        return parent

def test_graph_returns_dict_when_node():
    g = DummyGraph()
    result = g()
    assert isinstance(result, dict)
    assert "default" in result
    assert isinstance(result["default"], DummyNode)

def test_graph_returns_dict_when_dict():
    class DictGraph(Graph):
        def graph(self, *args, **kwargs):
            n1 = DummyNode(1)
            n2 = DummyNode(2)
            return {"a": n1, "b": n2}
    g = DictGraph()
    result = g()
    assert isinstance(result, dict)
    assert set(result.keys()) == {"a", "b"}
    assert all(isinstance(v, DummyNode) for v in result.values())

def test_graph_call_sets_cache():
    g = DummyGraph()
    ret = g()
    assert g._graph_cache is not None
    assert isinstance(g._graph_cache, dict)
    assert "default" in g._graph_cache
    assert isinstance(g._graph_cache["default"], DummyNode)

def test_graph_call_caching():
    g = DummyGraph()
    ret1 = g()
    ret2 = g()
    assert ret1 == ret2

def test_graph_method_must_be_overridden():
    class EmptyGraph(Graph):
        pass
    g = EmptyGraph()
    try:
        g()
    except NotImplementedError:
        assert True
    except Exception:
        # Should raise because graph() is not implemented
        assert True
    else:
        assert False, "Should raise due to not implemented graph()"




