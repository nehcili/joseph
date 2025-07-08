from abc import abstractmethod
from typing import Dict, List
import polars as pl


class FoodDataAPI(object):
    ###################################
    # methods supplied by the API
    ###################################
    @property
    @abstractmethod
    def nutrient_header(self) -> list:
        """
        Get a list of nutrient names as header for the nutrient values returned by get_food_nutrient_series
        """
        pass
    
    @abstractmethod
    def get_food_code(self, alias: str = None, food_name: str = None) -> int:
        """
        Get the food code for a given alias or food name. Only one of the two parameters is allowed.
        """
        pass
    
    @abstractmethod
    def get_food_name(self, alias: str = None, food_code: int = None) -> str:
        """
        Get the food name for a given alias or food code. Only one of the two parameters is allowed.
        """
        pass
    
    @abstractmethod
    def get_food_alias(self, food_code: int = None, food_name: str = None) -> str:
        """
        Get the food alias for a given food code or food name. Only one of the two parameters is allowed.
        """
        pass
    
    @abstractmethod
    def get_food_unit(self, alist: str = None, food_code: int = None, food_name: str = None) -> str:
        """
        Get the standard every day food unit for a given alias, food code, or food name. 
        Only one of the three parameters is allowed.

        e.g. lb for beef, oz for chicken, cup for rice.
        """
        pass

    @abstractmethod
    def get_food_nutrient_series(self, alias: str = None, food_code: int = None, food_name: str = None) -> pl.Series:
        """
        Get the nutrient series for a given food code or food name.
        Only one of the three parameters is allowed.
        The series's index is the nutrient header returened by the method `nutrient_header`
        """
        pass


class FnddsAPI(FoodDataAPI):
    """
    Data source: 
    https://www.ars.usda.gov/northeast-area/beltsville-md-bhnrc/beltsville-human-nutrition-research-center/food-surveys-research-group/docs/fndds-download-databases/
    """
    def __init__(
            self,
            nutrient_values_file_path: str = None,
            portions_and_weight_file_path: str = None,
        ):
        """
        Initialize the FoodDBAPI class.
        """

        self._alias_to_food_code: Dict[str:int] = None
        self._food_code_to_food_name: Dict[int:str] = None
        self._food_name_to_alias: Dict[str:str] = None
        self._nutrient_header: List[str] = None
        self._food_unit_by_food_code: Dict[int:str] = None

        self.nutrient_values_df: pl.DataFrame = None
        self.portions_and_weight_df: pl.DataFrame = None

    
    ###################################
    # methods supplied by the API
    ###################################
    @property
    def nutrient_header(self) -> list:
        return list(self._nutrient_header)
    
    def get_food_code(self, alias: str = None, food_name: str = None) -> int:
        """
        Get the food code for a given alias or food name.
        """
        if alias:
            return self._alias_to_food_code.get(alias)
        if food_name:
            return self._alias_to_food_code.get(self._food_name_to_alias.get(food_name))
        raise ValueError("Either alias or food_name must be provided.")

    def get_food_name(self, alias: str = None, food_code: int = None) -> str:
        """
        Get the food name for a given alias or food code.
        """
        if alias is not None:
            return self._food_code_to_food_name.get(self._alias_to_food_code.get(alias))
        elif food_code is not None:
            return self._food_code_to_food_name.get(food_code)
        else:
            raise ValueError("Either alias or food_code must be provided.")
        
    def get_food_alias(self, food_code: int = None, food_name: str = None) -> str:
        """
        Get the food alias for a given food code or food name.
        """
        if food_code is not None:
            return self._food_name_to_alias.get(self._food_code_to_food_name.get(food_code))
        elif food_name is not None:
            return self._food_name_to_alias.get(food_name)
        else:
            raise ValueError("Either food_code or food_name must be provided.")

    def get_food_unit(self, alist: str = None, food_code: int = None, food_name: str = None) -> str:
        if food_code is None:
            food_code = self.get_food_code(alias=alist, food_name=food_name)
        
        return self._food_unit_by_food_code.get(food_code)

    def get_food_nutrient_series(self, alias: str = None, food_code: int = None, food_name: str = None) -> pl.Series:
        """
        Get the nutrient series for a given food code or food name.
        """
        if food_code is None:
            food_code = self.get_food_code(alias=alias, food_name=food_name)
        
        return self._get_food_nutrient_series(food_code)
    
