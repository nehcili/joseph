import logging
from typing import Dict
import polars as pl
from src.data.fndds_api import FNDDSDataAPI
from src.common.base_graph import Graph, Node

logger = logging.getLogger(__name__)


__description__ = """
"""

class Item(object):
    __API : FNDDSDataAPI = None
    INDEX_COLS = [
        'Food code', 'Main food description', 'WWEIA category number', 'WWEIA category description'
    ]
    NUTRIENT_COLS = [
        'Energy (kcal)', 'Protein (g)', 'Carbohydrate (g)', 'Sugars, total\r\n(g)', 'Fiber, total dietary (g)',
        'Total Fat (g)', 'Fatty acids, total saturated (g)', 'Fatty acids, total monounsaturated (g)',
        'Fatty acids, total polyunsaturated (g)', 'Cholesterol (mg)', 'Retinol (mcg)', 'Vitamin A, RAE (mcg_RAE)',
        'Carotene, alpha (mcg)', 'Carotene, beta (mcg)', 'Cryptoxanthin, beta (mcg)', 'Lycopene (mcg)',
        'Lutein + zeaxanthin (mcg)', 'Thiamin (mg)', 'Riboflavin (mg)', 'Niacin (mg)', 'Vitamin B-6 (mg)',
        'Folic acid (mcg)', 'Folate, food (mcg)', 'Folate, DFE (mcg_DFE)', 'Folate, total (mcg)',
        'Choline, total (mg)', 'Vitamin B-12 (mcg)', 'Vitamin B-12, added\r\n(mcg)', 'Vitamin C (mg)',
        'Vitamin D (D2 + D3) (mcg)', 'Vitamin E (alpha-tocopherol) (mg)', 'Vitamin E, added\r\n(mg)',
        'Vitamin K (phylloquinone) (mcg)', 'Calcium (mg)', 'Phosphorus (mg)', 'Magnesium (mg)', 'Iron\r\n(mg)',
        'Zinc\r\n(mg)', 'Copper (mg)', 'Selenium (mcg)', 'Potassium (mg)', 'Sodium (mg)', 'Caffeine (mg)',
        'Theobromine (mg)', 'Alcohol (g)', '4:0\r\n(g)', '6:0\r\n(g)', '8:0\r\n(g)', '10:0\r\n(g)', '12:0\r\n(g)',
        '14:0\r\n(g)', '16:0\r\n(g)', '18:0\r\n(g)', '16:1\r\n(g)', '18:1\r\n(g)', '20:1\r\n(g)', '22:1\r\n(g)',
        '18:2\r\n(g)', '18:3\r\n(g)', '18:4\r\n(g)', '20:4\r\n(g)', '20:5 n-3\r\n(g)', '22:5 n-3\r\n(g)',
        '22:6 n-3\r\n(g)', 'Water\r\n(g)'
    ]

    def __init__(self, name: str, quantity: float, index_df: pl.DataFrame=None, nutrient_values_df: pl.DataFrame=None):
        """
        :param name: Name of the item.
        :param quantity: Quantity of the item in grams.
        :param index_df: Polars DataFrame with index columns for the item. ONLY available if the item is a source ingredient.
        :param nutrient_values_df: Polars DataFrame with nutrient values for 1g of the item.
        """
        if nutrient_values_df is None:
            df = self.__API.get(lazy=True)['nutrient_values']
            df : pl.DataFrame = df.filter(pl.col('Main food description') == name).collect()
            if df.is_empty():
                raise ValueError(f"Item {name} not found in the database.")
            elif df.shape[0] > 1:
                raise ValueError(f"Item {name} is not unique in the database. Found {df.shape[0]} rows.\
                                This error should not happen. Please check the database.")
            
            index_df = df.select(pl.col(*self.INDEX_COLS))
            nutrient_values_df = df.select(pl.col(*self.NUTRIENT_COLS)) / 100  # Normalize to per gram

        self._name = name

        assert quantity > 0, "Quantity must be a positive number."
        self._quantity = quantity

        # dataframe of 1 row
        # represents the nutrient values for 1g of the item
        self._index_df : pl.DataFrame = index_df
        self._nutrient_values_df : pl.DataFrame = nutrient_values_df
    
    @classmethod
    def set_api(cls, api: FNDDSDataAPI):
        """
        Set the API to be used for fetching data.
        """
        if not api.is_setup():
            api.setup()
        cls.__API = api

    def food_code(self):
        # FNDDS food code is unique for each food item
        return self._index_df['Food code'][0]
    
    @property
    def name(self) -> str:
        return self._name
    
    def set_name(self, name: str) -> "Item":
        self._name = name
        return self
    
    @property
    def quantity(self) -> float:
        return self._quantity
    
    def is_ingredient(self) -> bool:
        return self._index_df is not None
    
    def __add__(self, other: "Item") -> "Item":
        assert (self.name is not None) and (other.name is not None), \
            f"Output from a previous operation was not named. Current items are {self} and {other}."

        if self.is_ingredient() and other.is_ingredient() and self.food_code() == other.food_code():
            # If both items are the same ingredient, we can add the quantities
            return Item(
                name=self.name,
                quantity=self.quantity + other.quantity,
                index_df=self._index_df,
                nutrient_values_df=self._nutrient_values_df
            )
        else:
            return Item(
                name=None,
                quantity=self.quantity + other.quantity,
                index_df=None,
                nutrient_values_df=(self.quantity * self._df + other.quantity * other._df)/(self.quantity + other.quantity),
            )
    
    def __radd__(self, other: "Item") -> "Item":
        return self.__add__(other)

    def __mul__(self, other: float) -> "Item":
        assert other > 0, "Scaling factor must be positive."

        return Item(
            name=self.name,
            quantity=self.quantity * other,
            index_df=self._index_df,
            nutrient_values_df=self._nutrient_values_df
        )

    def __rmul__(self, other: float) -> "Item":
        return self.__mul__(other)

    def __repr__(self) -> str:
        return f"{self.name} ({self.quantity}g)"

    def get_nutrition_info(self, total=True) -> pl.DataFrame:
        """
        :return: 1-row only Polars DataFrame with nutrient values for the item.
        """
        res = self._nutrient_values_df
        if total:
            res = res * self.quantity

        return res


class ItemList(object):
    def __init__(self, items: Dict[int, Item] = None):
        if items is None:
            items = {}
        self._items = dict(items)

    def keys(self):
        return self._items.keys()
    
    def values(self):
        return self._items.values()
    
    def items(self):
        return self._items.items()

    def copy(self) -> "ItemList":
        # not a deep copy
        return ItemList(items=self._items)

    def __add__(self, other: "ItemList") -> "ItemList":
        res = self.copy()
        for value in other.values():
            res.add(value)

        return res

    def __mul__(self, other: float) -> "ItemList":
        return ItemList(
            items={ingredient * other for ingredient in self._items}
        )

    def __rmul__(self, other: float) -> "ItemList":
        return self.__mul__(other)
    
    def add(self, new_item: Item) -> "ItemList":
        """
        Add always adds a new copy of new_ingredient to the IngredientList.
        """
        key = new_item.food_code()

        if key in self._items:
            self._items[key] += new_item
        else:
            self._items[key] = new_item
        
        return self
    
    def get_shopping_list(self) -> pl.DataFrame:
        keys = sorted(self._items.keys())
        quantities = pl.Series("Quantity (g)", [self._items[key].quantity for key in keys])
        return pl.concat([
            self._items[key]._index_df.select('Main food description') for key in keys
        ]).with_columns(quantities)

    def get_nutrition_info(self, total=True) -> pl.DataFrame:
        """
        :return: Polars DataFrame with nutrient values for all items in the list.
        """
        return sum(
            [item.get_nutrition_info(total=True) for item in self._items.values()]
        )


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
        - `item_list`: an `ItemList` object that contains all the ingredients used in this step.
        - `output`: Item object that represents the output of the step.
        - `step_description`: list of str that describes the step. Index 0 is the first step.
        """
        output = super().forward(*args, **kwargs)
        assert isinstance(output, dict), "The output of the forward step must be a dict."
        assert 'item_list' in output and 'output' in output and 'step_description' in output, \
            "The output dict must contain 'item_list', 'output', and 'step_description' keys."
        assert isinstance(output['item_list'], ItemList), \
            "The 'item_list' key must contain an ItemList object."
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
    def __init__(self, name: str):
        super().__init__()
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
        - `item_list`: an `ItemList` object that contains all the ingredients used in this step.
        - `output`: Item object that represents the output of the step.
        - `step_description`: list of str that describes the step. Index 0 is the first step
        """
        output = super().forward()
        quantity = self._scale * grams

        # Rescale all items in the ingredient set and output by self._scale
        output['item_list'] *= quantity
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
            root: Node = self()
            assert isinstance(root, Node), "The output of a recipe graph must be a single Node."
            scale = 1.0 / root.forward(1)['output'].quantity
            root.backward(scale=scale)
            logger.info(f"Recipe graph {self.name} calibrated with scale {scale}.")

            self._is_calibrated = True
            self._graph_cache = root
    
    def __call__(self):
        self._calibrate()
        return super().__call__()
            









