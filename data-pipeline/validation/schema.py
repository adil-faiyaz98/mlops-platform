import pandera as pa
from pandera import Column, Check,errors

class MyDataSchema(pa.SchemaModel):
    """Define the schema for your data."""
    col1: Column(pa.Int, Check.greater_than(0))
    col2: Column(pa.String, Check.isin(['a', 'b', 'c']))
    col3: Column(pa.Float, nullable=True)

    class Config:
        strict = True  # Enforce schema strictly

def checkTest(name) -> None: #To have code that is correct and valid
    try:
        MyDataSchema.validate(name, lazy=True) #Validate codes
    except errors.SchemaErrors as err: # if type is incorrect
        raise ValueError(err) #Raise error
    except Exception as e: #Catch all errors
        raise ValueError(f"Error validating data: {e}") #Raise error