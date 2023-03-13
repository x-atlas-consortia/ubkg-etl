import pandas as pd


class Codes:

    def __init__(self, filename: str) -> None:
        self.df = pd.read_csv(filename, skiprows=1)

    def find_codeid(self, codeid: str) -> str:
        return not self.df.query(f"`CodeID:ID` == '{codeid}'").empty

