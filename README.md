# Joseph

## Version 1
### Goal
1. No user interface is needed. All configs are to be inputed by hand in config files.
2. There is generate.py file that can be run to email all the details to my email.
3. Content of email
    1. shopping list
    2. recipe of each meal
    2. total nutrient count and pie chart for contribution of each meal
4. Repotoire of recipes to automatically rotate

### Supports
1. scaling/different serving of the same recipe
    - The recipe may be 2 serving, but the serving size should be specified when building the graph
2. auto collects all the ingredients

### System 
#### Recipe
- Operations/steps are graph based. Each operation is a `Node` class.
- Each recipe is an DA graph of nodes. Contain this with `Graph` class.
- For version 1, each recipe is a `Graph` of a single `Node`.
- A simple topological sort is implemented to get all the operations/steps together to string a recipe.

## Initial ideas
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