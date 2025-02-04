from sqlalchemy.ext.automap import automap_base
from ..database.config import prelude_engine

# Create the base class
Base = automap_base()

# Reflect the tables
Base.prepare(autoload_with=prelude_engine)

# Get the models
Alert = Base.classes.Prelude_Alert
Impact = Base.classes.Prelude_Impact
Classification = Base.classes.Prelude_Classification
Address = Base.classes.Prelude_Address
DetectTime = Base.classes.Prelude_DetectTime
Analyzer = Base.classes.Prelude_Analyzer
Node = Base.classes.Prelude_Node
Reference = Base.classes.Prelude_Reference
Service = Base.classes.Prelude_Service
AdditionalData = Base.classes.Prelude_AdditionalData
CreateTime = Base.classes.Prelude_CreateTime
Process = Base.classes.Prelude_Process
Source = Base.classes.Prelude_Source
Target = Base.classes.Prelude_Target
