import pytest
import polars as pl
from src.common.utils import assert_pl_df_equal
from src.recipes.base_recipe import Item, ItemList, Step, SourceStep, Recipe


# Dummy API and DataFrame for Item
class DummyAPI:
    def __init__(self):
        self._setup = False
        self._df = pl.DataFrame({
            'Food code': [123],
            'Main food description': ['Apple'],
            'WWEIA category number': [1],
            'WWEIA category description': ['Fruit'],
            'Energy (kcal)': [52.0],
            'Protein (g)': [0.3],
            'Carbohydrate (g)': [14.0],
            'Sugars, total\r\n(g)': [10.0],
            'Fiber, total dietary (g)': [2.4],
            'Total Fat (g)': [0.2],
            # ... add all NUTRIENT_COLS as needed for tests
        })

    def is_setup(self):
        return self._setup

    def setup(self):
        self._setup = True

    def get(self, lazy=True):
        return {'nutrient_values': self._df.lazy()}


def make_item(name="Apple", food_code=123, quantity=100):
    index_df = pl.DataFrame({
        'Food code': [food_code],
        'Main food description': [name],
        'WWEIA category number': [1],
        'WWEIA category description': ['Fruit'],
    })
    nutrient_values_df = pl.DataFrame({
        'Energy (kcal)': [0.52],
        'Protein (g)': [0.003],
        'Carbohydrate (g)': [0.14],
        'Sugars, total\r\n(g)': [0.10],
        'Fiber, total dietary (g)': [0.024],
        'Total Fat (g)': [0.002],
    })
    return Item(name, quantity, index_df=index_df, nutrient_values_df=nutrient_values_df)

def test_item_init_and_properties():
    item = make_item()
    assert item.name == "Apple"
    assert item.quantity == 100
    assert item.is_ingredient()
    assert isinstance(item._index_df, pl.DataFrame)
    assert isinstance(item._nutrient_values_df, pl.DataFrame)


def test_item_add_same_ingredient():
    item1 = make_item(quantity=50)
    item2 = make_item(quantity=70)
    item3 = item1 + item2
    assert item3.name == "Apple"
    assert item3.quantity == 120
    assert_pl_df_equal(item3._nutrient_values_df, item1._nutrient_values_df)

def test_item_mul():
    item = make_item(quantity=10)
    item2 = item * 3
    assert item2.quantity == 30
    assert item2.name == item.name
    assert_pl_df_equal(item2._nutrient_values_df, item._nutrient_values_df)

def test_item_repr():
    item = make_item(quantity=42)
    assert "Apple" in repr(item)
    assert "42g" in repr(item)

def test_item_get_nutrition_info_total():
    item = make_item(quantity=10)
    df = item.get_nutrition_info(total=True)
    assert isinstance(df, pl.DataFrame)
    assert df['Energy (kcal)'][0] == pytest.approx(0.52 * 10)

def test_item_get_nutrition_info_per_gram():
    item = make_item(quantity=10)
    df = item.get_nutrition_info(total=False)
    assert df['Energy (kcal)'][0] == pytest.approx(0.52)

def test_itemlist_add_and_keys():
    item1 = make_item(quantity=10)
    item2 = make_item(quantity=20)
    ilist = ItemList()
    ilist.add(item1)
    ilist.add(item2)
    assert 123 in ilist.keys()
    assert ilist._items[123].quantity == 30

def test_itemlist_mul():
    item = make_item(quantity=10)
    ilist = ItemList()
    ilist.add(item)
    ilist2 = ilist * 2
    for v in ilist2.values():
        assert v.quantity == 20

def test_itemlist_get_shopping_list():
    item = make_item(quantity=10)
    ilist = ItemList()
    ilist.add(item)
    df = ilist.get_shopping_list()
    assert "Main food description" in df.columns
    assert "Quantity (g)" in df.columns
    assert df["Quantity (g)"][0] == 10

def test_itemlist_get_nutrition_info():
    item = make_item(quantity=10)
    ilist = ItemList()
    ilist.add(item)
    df = ilist.get_nutrition_info()
    assert isinstance(df, pl.DataFrame)
    assert df['Energy (kcal)'][0] == pytest.approx(0.52 * 10)

def test_step_forward_checks(monkeypatch):
    class DummyNode:
        def forward(self, *args, **kwargs):
            return {
                'item_list': ItemList(),
                'output': make_item(),
                'step_description': "desc"
            }
    step = Step()
    monkeypatch.setattr(Step, "forward", DummyNode().forward)
    # Should not raise
    out = Step.forward(step)
    assert isinstance(out, dict)
    assert 'item_list' in out
    assert 'output' in out
    assert 'step_description' in out


class DummySourceStep(SourceStep):
    def __init__(self, name, food_code, initial_scale):
        super().__init__(name)
        self._scale = 1.0
        self._initial_scale = initial_scale
        self.food_code = food_code

    def _forward(self, grams):
        item = make_item(name=self.name, food_code=self.food_code, quantity=grams * self._initial_scale)
        item_list = ItemList({self.food_code: item})

        return {
            'item_list': item_list,
            'output': item,
            'step_list': []
        }

class DummyStep(Step):
    def _forward(self, in1: dict, in2: dict) -> dict:
        item1 = in1['output']
        item2 = in2['output']
        item3 = (item1 + item2).set_name("mixture")

        step_list = in1['step_list'] + in2['step_list']
        step_list.append(f"Combine {item1} and {item2} to make {item3}")
        
        item_list = in1['item_list'] + in2['item_list'] 

        return {
            'item_list': item_list,
            'output': item3,
            'step_list': step_list
        }


def test_sourcestep_backward_and_forward():
    step = DummySourceStep("source", 1, 7)
    out = step.forward(grams=1)
    assert out['output'].quantity == 7

    # Test backward sets scale
    step._backward(1/7)
    assert abs(step._scale - 1/7) < 1e-6  # Check scale is set correctly

    out = step.forward(grams=10)
    assert abs(out['output'].quantity - 10) < 1e-6  # Check output is scaled correctly

def test_multiple_step_backward_and_forward():
    step1 = DummySourceStep("Apple", 1, 3)
    step2 = DummySourceStep("Banana", 2, 9)

    step3 = DummyStep()(step1, step2)

    out = step3.forward(grams=1)
    assert out['output'].name == "mixture"
    assert out['output'].quantity == 12  # 3 + 9

    step3.backward(scale=1/12)
    assert abs(step1._scale - 1/12) < 1e-6

    out = step3.forward(grams=1)
    assert abs(out['output'].quantity - 1) < 1e-6  # Check output is scaled correctly
    assert out['output'].name == "mixture"
    
    items = out['item_list']._items
    assert items[1].name == "Apple"
    assert items[2].name == "Banana"
    assert items[1].quantity == 3/(3+9)
    assert items[2].quantity == 9/(3+9)

def test_recipe_calibrate(monkeypatch):
    class DummyGraph(Recipe):
        def graph(self):
            step1 = DummySourceStep("Apple", 1, 3)
            step2 = DummySourceStep("Banana", 2, 9)

            step3 = DummyStep()(step1, step2)
            return step3

    recipe = DummyGraph("test_recipe")
    root = recipe()
    assert recipe.is_calibrated
    out = root['default'].forward(grams=1)
    assert out['output'].name == "mixture"
    assert out['output'].quantity == 12

    