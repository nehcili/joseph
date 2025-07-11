from src.recipes.base_recipe import Item, ItemList, SourceStep, Step


class GetItem(SourceStep):
    """
    Get item from a source.
    """
    def __init__(self, name: str, quantity: int = 1):
        super().__init__(name)
        self.quantity = quantity

    def _forward(self, grams: float):
        item = Item(name=self.name, quantity=self.quantity) * grams
        item_list = ItemList()
        item_list.add(item)
        
        return {
            'item_list': item_list,
            'output': item,
            'step_description': f"Get {item}"
        }

class Make(Step):
    def _forward(self, *items):
        return super()._forward(*args, **kwargs)