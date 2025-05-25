# Joseph

## Version 1
### Data
- Obtained from `https://www.ars.usda.gov/northeast-area/beltsville-md-bhnrc/beltsville-human-nutrition-research-center/food-surveys-research-group/docs/fndds-download-databases/`
- Food and Beverage: just a file with descriptions of what the food and beverage is

- Ingredeints contains
    - food name and `food code`
    - For each food item, a list of its 
        - `ingredients codes` and description that makes up the food
        - weight of ingredients and related portioning info

- Nutrient Values
    - `food code` and food descrption
    - nutrious value of the food per 100 grams

- Food and Beverages
    - mapping to other database codes using `food code`

- Ingredient Nutritent Values
    - Provides columnar nutrient values for each ingredient by `ingredient code`. 
    - actual `nutrient code` and description is it's own columns and value is another (i.e. columnar format)

- Portion and Weights
    - a map of food by `food code` of common portion (e.g. cup, fl oz) to grams.

### System
- System is a directed acyclic graph.
- A node contains 
    - node specs
        - name: str
        - unit: str (output_unit)
    - _quantity_in_grams
    - _nutrient_values: a tensor. This tensor can be `None`. It is the sum of its immediate children when computed. But computation is lazy by default.
    - _children: a list of nodes
    - _priority: int: a flag that indicates priority:
        - 0 = can be done in background concurrently and can stack
        - 1 = cannot be done in background, but can have other processes running in the background
        - 2 = does not allow any concurrency
    - span: float: a number that indicates how many seconds does the process take