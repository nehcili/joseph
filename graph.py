from abc import abstractmethod
import logging
from typing import Any

logger = logging.getLogger(__name__)


class Node(object):
    """
    Graph structure
    ===============

    `Node` class implements a directed acyclic graph (DAG) where each node is a task with certain time
    cost. A node is also known as a vertex. 
    
    A minimal cost ordering (MCO) of a DAG graph is a linear ordering of the graph (respecting dependencies) such that the sum of the
    time costs of the tasks in the ordering is minimized. The ordering is minimal if there is no other ordering
    of the graph with a lower cost. This MCO might not be unique. However, we implement a deterministic
    algorithm to find a particular ordering. 

    MCO is a NP problem. To reduce run time, we introduce a few heuristics to reduce the size of the graph. 
    In the mean time, certain tasks specific constraints are also added to the graph. In total, we have 3
    types of constraints and properties:
    1. Task specifc: Each node can be marked as a background task. This allows another task to be run in parallel with the background task.
    2. Task specific/Mergeable: identical subgraphs can be merged into a single node. (Details below under `Mergeing` subsection).
    3. Contractable: a node can be marked as contractable. This means that the node can be contracted into a single node with other vertices. 
    (Details below under `Contracting` subsection).

    During impplementation. This graph is built from the vertices in 2 stages:
    1. Merge all subgraphs which are equivalent (defined below). 
    2. Contract all subgraphs whose vertices marked as `is_contractable` are to be contracted into a single node.

    After the graph is built, we run through all possible topological orderings of the graph and pick the ordering with least
    cost. (Details below under `Cost computation` subsection).

    Cost computation
    ================
    Once a graph is flattened into a linear ordering, we sum up all costs of tasks in the ordering, with care taken to account for background tasks.

    Merging
    =======
    Identifying subgraph isomorphism is a NP problem. To reduce run time, we merge from the leaves up to the root only. We will introduce a hash to each node
    that serializes/hashes the node and all of its children resursively. That is, we will merge maximum subgraphs starting from the leaves. From a human
    task performance perspective, this is a reasonable action.

    Contracting
    ===========
    The main purpose
    of this contraction is to avoid MCO algorithm to waste time on a graph as follows.
    A -> B -> C --+
                  |
                  +-> D
                  |
    E -> F -> G --+
    A sensible linear ordering is A -> B -> C -> E -> F -> G -> D. While A -> E -> B -> F -> C -> G -> D is not sensible from a the persepctive
    of a human worker working on a sequence of tasks. In this case, we contract A -> B -> C and E -> F -> G into single nodes.

    In the case where a nonlinear subgraph is marked contractable, we will contract the subgraph into a single node in the MCO algorithm. But
    the end ordering of the contracted subgraph will be any linear ordering of the subgraph. This might not be optimal. A warning will be issued
    in this case.   

    Specification
    ==============
    - A node has exactly one output. Multiple outputs are not implemented at the moment. Otherwise, the `Node`
    needs to specify output type.
    """
    def __init__(self):
        self._children = None
        self._parents = None


    @property
    @abstractmethod
    def is_background(self) -> bool:
        """
        Check if the node is a background task. A background task is a task that can be run in parallel with other tasks.
        """
        pass
    
    @property
    @abstractmethod
    def is_contractable(self) -> bool:
        """
        Check if the node is contractable. 
        """
        pass

    @property.setter
    @abstractmethod
    def is_contractable(self, value: bool):
        """
        Set the node as contractable.
        """
        pass

    @abstractmethod
    def get_hash(self) -> str:
        """
        Get the hash of the node. The hash is a unique identifier for the node and its children resursively. 
        That is, the hash is a unique identifier for maximum subgraphs starting at the node.

        Hash is dynamically computed, since graph might change.
        """

    def forward(self, *args, **kwargs) -> Any:
        """
        Does the actual computation of the node. This method is called when the graph is built.
        Computation doesn't require MCO ordering.
        """
        pass

    def __call__(self, *args, **kwargs) -> "Node":
        """
        Call this method to set the children of the node. The output of the children will be passed to the forward method of the node,
        in the order of the arguments of takes. No recursive args/kwargs will be allowed.

        We don't 

        args/kwargs can be one of
        - Node
        - list of Nodes
        - tuple of Nodes
        - dict of Nodes
        """

        if self._children is not None:
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


    def get_children(self) -> list:
        """
        Get the children of the node. The children are the nodes that depend on this node.
        """
        pass


    

    

