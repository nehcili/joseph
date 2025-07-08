import logging
from typing import Dict, Set
import polars as pl
from src.common.graph.base import Graph, Node

logger = logging.getLogger(__name__)


__description__ = """
"""

class Item(object):
    def __hash__(self):
        pass

    def __add__(self, other) -> "Item":
        pass

    def __mul__(self, other: float) -> "Item":
        pass

    def __rmul__(self, other: float) -> "Item":
        return self.__mul__(other)

    def __str__(self) -> str:
        pass

    def get_quantity(self) -> float:
        """
        Get the quantity of the item in grams.
        """
        pass

    def get_nutrition_info(self) -> pl.Series:
        """
        Get the nutrition information of the item.
        """
        pass

    def to_series(self) -> pl.Series:
        """
        Convert the Item to a Polars Series with the following schema:
        - `name`: str
        - `quantity`: float
        - `unit`: str
        - `grocery_store`: str  # grocery store for the item
        - `food_code`: str  # food code for the item
        """
        

class IngredientSet(object):
    def __init__(self, items: Set[Item] = None):
        """
        Initialize an ItemSet with a dictionary of items.
        """
        self._items : Set[Item] = items if items is not None else {}

    def __add__(self, other: "IngredientSet") -> "IngredientSet":
        """
        Add two ItemSets together.
        """
        pass

    def __mul__(self, other: float) -> "IngredientSet":
        """
        Scale the ItemSet by a float.
        """
        pass

    def __rmul__(self, other: float) -> "IngredientSet":
        """
        Scale the ItemSet by a float.
        """
        return self.__mul__(other)
    
    def add(self, item: Item) -> "IngredientSet":
        """
        Add an Item to the ItemSet.
        """
        pass
    
    def remove(self, item_name: str) -> "IngredientSet":
        pass
    
    def to_dataframe(self) -> pl.DataFrame:
        """
        Convert the ItemSet to a Polars DataFrame with schema:
        - `name`: str
        - `alias`: str  # alias for the item
        - `quantity`: float
        - `unit`: str
        - `grocery_store`: str  # grocery store for the item
        - `food_code`: str  # food code for the item
        """
        series_list = [item.to_series() for item in self._items.values()]
        schema = ["name", "alias", "quantity", "unit", "grocery_store", "food_code"]
        if not series_list:
            return pl.DataFrame(schema=schema)
        return pl.DataFrame(series_list, schema=schema)


class Step(Node):
    """
    Step is a step in a recipe. We model it as a Node in a graph.

    Specification
    =============
    - Input to the forward step is float that scales the computation. You can think of it as a number of servings.
    - There is no backward step (to scale to the correct serving). 
        All calibration is done in the Graph stage. That is, `Recipe(Graph)` will take care of that.
    - The _forward step should return a dict of
        - `ingredients`: a dict of all `Item` objects that are used in in graph
        - An `Item` object that represents the output of the step, which can be used in the next step.
    """
    def forward(self, *args, **kwargs) -> dict:
        """
        "return dict:
        Must return a dict with the following keys:
        - `ingredient_set`: an `IngredientSet` object that contains all the ingredients used in this step.
        - `output`: Item object that represents the output of the step.
        - `step_description`: list of str that describes the step. Index 0 is the first step.
        """
        output = super().forward(*args, **kwargs)
        assert isinstance(output, dict), "The output of the forward step must be a dict."
        assert 'ingredient_set' in output and 'output' in output and 'step_description' in output, \
            "The output dict must contain 'ingredient_set', 'output', and 'step_description' keys."
        assert isinstance(output['ingredient_set'], IngredientSet), \
            "The 'ingredient_set' key must contain an IngredientSet object."
        assert isinstance(output['output'], Item), \
            "The 'output' key must contain an Item object."
        assert isinstance(output['step_description'], str), \
            "The 'step_description' key must contain a str."
        return output
    
class SourceStep(Step):
    """
    SourceStep is a step that provides the initial ingredients for the recipe.
    It is a special type of Step that does not depend on any previous steps.
    """
    def __init__(self, name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self._scale = 1.0  # Default scale for the source step

    def _backward(self, scale: float, depth: int = 0, parent: Node = None, _state: Dict = None) -> dict:
        """
        Set the scale for the source step.
        This is used to determine how many servings the source step provides.
        """
        if not isinstance(scale, (int, float)) or scale <= 0:
            raise ValueError("Scale must be a positive number.")
        logger.info(f"Setting scale for SourceStep {self.name} to {scale}")
        self._scale = scale

    def forward(self, grams: float) -> dict:
        """
        "return dict:
        Must return a dict with the following keys:
        - `ingredient_set`: an `IngredientSet` object that contains all the ingredients used in this step.
        - `output`: Item object that represents the output of the step.
        - `step_description`: list of str that describes the step. Index 0 is the first step
        """
        output = super().forward()
        quantity = self._scale * grams

        # Rescale all items in the ingredient set and output by self._scale
        output['ingredient_set'] *= quantity
        output['output'] *= quantity
        output['step_description'] = output['step_description'].format(quantity=quantity)

        return output
        

class Recipe(Graph):
    def __init__(self, name : str):
        super().__init__()
        self.name = name
        self._is_calibrated = False

    @property
    def is_calibrated(self) -> bool:
        """
        Check if the recipe has been calibrated.
        Calibration means that the recipe has been set up with the correct serving sizes.
        """
        return self._is_calibrated
    
    def _calibrate(self):
        """
        Calibrate the recipe graph.
        This method is called automatically when the graph is built.
        It sets the scale for the recipe based on the output of the root node.
        """
        if not self.is_calibrated:
            logger.info(f"Calibrating recipe graph for {self.name}.")
            root: Node = self.graph()
            assert isinstance(root, Node), "The output of a recipe graph must be a single Node."
            scale = 1.0 / root.forward(1)['output'].quantity
            root.backward(scale=scale)
            logger.info(f"Recipe graph {self.name} calibrated with scale {scale}.")
            self._is_calibrated = True
    
    def _graph(self):
        self._calibrate()
        return super()._graph()









