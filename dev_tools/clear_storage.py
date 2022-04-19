import pandas as pd

fieldnames = ['tgid', 'num', 'fio', 'time', 'longitude', 'latitude', 'status']
data = pd.DataFrame(columns=fieldnames)
data.to_excel("storage.xlsx", index=False)