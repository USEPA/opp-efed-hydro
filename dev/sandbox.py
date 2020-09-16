import pandas as pd
import numpy as np

import os
table = r"A:\opp-efed\sam\hydro\Tables\nhd_map.csv"

table = pd.read_csv(table)

news = pd.DataFrame(np.array([os.path.split(t) for t in table.table]), columns=['path', 'table'])
news['path'] = news.path.str.lstrip("\\")
table = pd.concat([news, table.iloc[:, 1:]], axis=1)

print(table.to_csv(r"A:\opp-efed\sam\hydro\Tables\nhd_map.csv", index=None))