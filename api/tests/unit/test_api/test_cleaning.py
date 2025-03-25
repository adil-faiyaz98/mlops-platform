import pandas as pd
from api.data_processing.cleaning import remove_duplicates

def test_remove_duplicates():
    data = {'col1': [1, 2, 2, 3], 'col2': ['a', 'b', 'b', 'c']}
    df = pd.DataFrame(data)
    df_no_duplicates = remove_duplicates(df)
    assert len(df_no_duplicates) == 3