from typing import Dict
import polars as pl
from src.common.graph.base import Node

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

    def get_quantity(self, unit='gram') -> float:
        """
        Get the quantity of the item.
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
        pass


class IngredientSet(object):
    def __init__(self, items: Dict[str, Item] = None):
        """
        Initialize an ItemSet with a dictionary of items.
        """
        self.items = items if items is not None else {}

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
        - `quantity`: float
        - `unit`: str
        - `grocery_store`: str  # grocery store for the item
        - `food_code`: str  # food code for the item
        """
        pass



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
    def _backward(self, *args, **kwargs):
        return super()._backward(*args, **kwargs)

    def forward(self, *args, **kwargs) -> dict:
        """
        "return dict:
        Must return a dict with the following keys:
        - `ingredient_set`: an `IngredientSet` object that contains all the ingredients used in this step.
        - `output`: Item object that represents the output of the step.
        - `step_description`: str that describes the step.
        """
        output = super().forward(*args, **kwargs)
        if not isinstance(output, dict):
            raise ValueError("The output of the forward step must be a dict.")
        if 'ingredient_set' not in output or 'output' not in output or 'step_description' not in output:
            raise ValueError("The output dict must contain 'ingredient_set', 'output', and 'step_description' keys.")
        if not isinstance(output['ingredient_set'], IngredientSet):
            raise ValueError("The 'ingredient_set' key must contain an IngredientSet object.")
        if not isinstance(output['output'], Item):
            raise ValueError("The 'output' key must contain an Item object.")
        if not isinstance(output['step_description'], str):
            raise ValueError("The 'step_description' key must contain a str.")
        return output
    
class SourceStep(Step):
    """
    SourceStep is a step that provides the initial ingredients for the recipe.
    It is a special type of Step that does not depend on any previous steps.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scale = 1.0  # Default scale for the source step

    def set_scale


    def forward(self, grams: float) -> dict:
        output = super().forward(*args, **kwargs)
        if not isinstance(output, dict):
            raise ValueError("The output of the forward step must be a dict.")
        if 'ingredient_set' not in output or 'output' not in output or 'step_description' not in output:
            raise ValueError("The output dict must contain 'ingredient_set', 'output', and 'step_description' keys.")
        if not isinstance(output['ingredient_set'], IngredientSet):
            raise ValueError("The 'ingredient_set' key must contain an IngredientSet object.")
        if not isinstance(output['output'], Item):
            raise ValueError("The 'output' key must contain an Item object.")
        if not isinstance(output['step_description'], str):
            raise ValueError("The 'step_description' key must contain a str.")
        return output


    
