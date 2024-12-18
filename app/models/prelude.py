from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import relationship
from ..database.config import engine, metadata

Base = automap_base(metadata=metadata)

# Reflect the tables
Base.prepare()

# Map the tables to classes
Alert = Base.classes.Prelude_Alert
AdditionalData = Base.classes.Prelude_AdditionalData
Address = Base.classes.Prelude_Address
Analyzer = Base.classes.Prelude_Analyzer
Assessment = Base.classes.Prelude_Assessment
Classification = Base.classes.Prelude_Classification
CreateTime = Base.classes.Prelude_CreateTime
DetectTime = Base.classes.Prelude_DetectTime
Impact = Base.classes.Prelude_Impact
Node = Base.classes.Prelude_Node
Process = Base.classes.Prelude_Process
Reference = Base.classes.Prelude_Reference
Service = Base.classes.Prelude_Service
Source = Base.classes.Prelude_Source
Target = Base.classes.Prelude_Target
