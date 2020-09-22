import pandas as pd
import numpy as np

comid = np.array(['123', '234', '345', '456'])

nodes = pd.DataFrame({'a': ['234', '234', '345', '345'], 'b': ['123', '456', '123', '456']})

# Create an alias for nodes
convert = pd.Series(np.arange(comid.size), index=comid)
nodes = nodes.apply(lambda row: row.map(convert)).fillna(-1).astype(np.int32)

print(nodes)