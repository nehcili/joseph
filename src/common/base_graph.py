from abc import abstractmethod
from copy import deepcopy
import logging
from typing import Any, Dict, Union


logger = logging.getLogger(__name__)


class Node(object):
    """
    Graph structure
    ===============

    `Node` class implements a directed acyclic graph (DAG) where each node is a task with certain time
    cost. A node is also known as a vertex. 
    
    Specification
    ==============
    - A `Node` has a _children attribute, which is a tuple of 1) ordered `Node` and 2) dict of `Node's
    - Use `__call__` to build the graph (by taking in childrens)
    - Override `_forward` to specify this `Node''s computation. Use forward to compute the output of the graph.
        - You can provide func to forward method, which will be used to compute the output of the node. Default is `self._forward`.
    - Override `_backward` to specify how to build the graph in reverse order. Call `backward` to compute the graph in reverse order.
        - You can provide func to backward method, which will be used for reverse computation. Default is `self._backward`.
        - `_state` is a protected keyword of kwargs. Do not populate it in backward's kwargs.
    """
    def __init__(self):
        super().__init__()
        self._children: tuple = None

    @property
    def children(self) -> tuple:
        """
        Note that we return children without copying. So any manipulation will change the actual children of the node
        """
        return self._children

    def __call__(self, *args, **kwargs) -> "Node":
        """
        Call this method to set the children of the node. The output of the children will be passed to the forward method of the node,
        in the order of the arguments passed. No recursive args/kwargs will be allowed.

        args/kwargs can be one of
        - Node
        - list of Nodes
        - tuple of Nodes
        - dict of Nodes
        """

        if self.children is not None:
            logger.warning("Overwriting children of node %s", self)

        _invalid_msg = "Invalid argument type. Expected Node or list/tuple/dict of Nodes."
        _args = []
        for arg in args:
            if isinstance(arg, Node):
                _args.append(arg)
            elif isinstance(arg, (list, tuple)):
                assert all(isinstance(i, Node) for i in arg), _invalid_msg
                _args.append(arg)
            elif isinstance(arg, dict):
                assert all(isinstance(i, Node) for i in arg.values()), _invalid_msg
                _args.append(arg)
            else:
                raise ValueError(_invalid_msg)
            
        _kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, Node):
                _kwargs[key] = value
            elif isinstance(value, (list, tuple)):
                assert all(isinstance(i, Node) for i in value), _invalid_msg
                _kwargs[key] = value
            elif isinstance(value, dict):
                assert all(isinstance(i, Node) for i in value.values()), _invalid_msg
                _kwargs[key] = value
            else:
                raise ValueError(_invalid_msg)
            
        self._children = (_args, _kwargs)

        return self
    
    ######################################
    # Override these methods
    ######################################
    def _forward(self, *args, **kwargs) -> Any:
        """
        Does the actual computation of the node. This method is called when the graph is built.
        Computation doesn't require MCO ordering.

        Must return fresh copy of any input, if mutation is required.
        """
        pass
    
    def _backward(self, *args, depth=0, parent=None, _state=None, **kwargs) -> dict:
        """
        Parameters
        ===========
        :dict _state:
        A dict containing the state of the node. This is used to keep track of the depth and parent of the node in the graph. Must contain:
            - `depth`: current depth of the node in the graph
            - `parent`: parent of the current node
        "returns dict:
        - A dict containing the data for the child node in DFS traversal. No need to return the parent or depth, as these will be taken 
        care of by the `build` method.
        - Must return a distinct copy of the `_state` dict as to avoid accidental mutation of the state.

        Performs DFS on the tree to do any required backward building such as
        - scaling each node (for different servings)
        - building recipe
        """
        return None

    ######################################
    # public methods to use
    ######################################
    def forward(self, *args, **kwargs) -> Any:
        """
        Computes the tree from leaves up to the root.

        How it works
        =============
        - *args and **kwargs are passed to the leaf nodes. They are not used by the non-leaf nodes.
        - outputs of children are input into current node's _forward method.
        """

        # if a node is a leaf.
        if self.children is None:
            return self._forward(*args, **kwargs)

        # compute recursively all non leaf nodes.
        args = []
        kwargs = {}

        _invalid_msg = "Invalid argument type. Expected Node or list/tuple/dict of Nodes."

        args_children, kwargs_children = self.children  # These are the children of the node, which are Nodes or lists/tuples/dicts of Nodes.
        input_args, input_kwargs = [], {}  # These are the output of the children.
        for value in args_children:
            if isinstance(value, Node):
                input_args.append(value.forward(*args, **kwargs))
            elif isinstance(value, (list, tuple)):
                input_args.append([node.forward(*args, **kwargs) for node in value])
            elif isinstance(value, dict):
                input_args.append({k: node.forward(*args, **kwargs) for k, node in value.items()})
            else:
                raise ValueError(_invalid_msg)
        
        for key, value in kwargs_children.items():
            if isinstance(value, Node):
                input_kwargs[key] = value.forward(*args, **kwargs)
            elif isinstance(value, (list, tuple)):
                input_kwargs[key] = [node.forward(*args, **kwargs) for node in value]
            elif isinstance(value, dict):
                input_kwargs[key] = {k: node.forward(*args, **kwargs) for k, node in value.items()}
            else:
                raise ValueError(_invalid_msg)

        return self._forward(*input_args, **input_kwargs)

    def backward(self, *args, depth=0, parent=None, _state=None, **kwargs) -> "Node":
        """
        Computes the tree from root down to the leaves.

        Specification
        ===========
        `_state` is a protected keyword of kwargs. Do not populate it.
        this state can be mutated by any method of this Node (including _backward). But a new copy (of possibly processed `_state`) must be passed to the children nodes.
        """
        # if is root node, we need to build the state.
        if _state is None:
            _state = {}

        # if a node is a leaf.
        if self.children is None:
            self._backward(*args, depth=depth, parent=parent, _state=_state, **kwargs)
            return self

        # build this Node
        _state = self._backward(*args, depth=depth, parent=parent, _state=_state, **kwargs)

        # recursively build all children nodes.
        args_children, kwargs_children = self.children
        for child in args_children:
            cur_state = deepcopy(_state)
            child.backward(*args, depth=depth, parent=parent, _state=cur_state, **kwargs)
        
        for _, child in kwargs_children.items():
            cur_state = deepcopy(_state)
            child.backward(*args, depth=depth, parent=parent, _state=cur_state, **kwargs)

        return self


class Graph(object):
    def __init__(self):
        super().__init__()
        """
        The root of the graph is uniquely determined by args and kwargs. So we cache the result
        """
        self._graph_cache = None
        self._graph_cache_args = None
        self._graph_cache_kwargs = None

    def __call__(self, *args, **kwargs) -> Dict[str, "Node"]:
        # Cache the result so __call__ and direct _graph() return the same object
        if (
            self._graph_cache is not None
            and self._graph_cache_args == args
            and self._graph_cache_kwargs == kwargs
        ):
            return self._graph_cache
        result = self.graph(*args, **kwargs)
        if isinstance(result, Node):
            result = {"default": result}
        elif isinstance(result, dict):
            pass
        else:
            raise ValueError("graph() must return a Node or dict of Nodes")
        self._graph_cache = result
        self._graph_cache_args = args
        self._graph_cache_kwargs = kwargs
        return result

    #######################################
    # Override these methods
    #######################################
    @abstractmethod
    def graph(self, *args, **kwargs) -> Union["Node", Dict[str, "Node"]]:
        """
        Use the grpah method to build DAG.

        Example
        =======
        x = Source(data='example.csv')()
        x = Wash()(x)
        x = Cut()(x)
        x = CookOnStove(time=10)(x)

        return x
        """
        pass
