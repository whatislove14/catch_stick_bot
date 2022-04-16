import pandas


def new_sig(tgid, num, fio, time, longitude, latitude):
    data = pandas.read_excel("storage.xlsx", index_col=False)
    data = data.append({'tgid': str(tgid), 'num': num, 'fio': fio, 'time': time, 'longitude': longitude, 'latitude': latitude, 'status': 'registered'}, ignore_index=True)
    data.to_excel("storage.xlsx", index=False)

def get_sig(num):
    data = pandas.read_excel("storage.xlsx", index_col=False)
    for index, row in data.iterrows():
        if int(row['num']) == int(num):
            return row
    return None

def get_all_sigs_byid(tgid):
    all_sigs = []
    data = pandas.read_excel("storage.xlsx", index_col=False)
    for index, row in data.iterrows():
        if int(row['tgid']) == int(tgid):
            all_sigs.append(row)
    return all_sigs

def get_all_sigs():
    all_sigs = []
    data = pandas.read_excel("storage.xlsx", index_col=False)
    for index, row in data.iterrows():
        all_sigs.append(row)
    return all_sigs

def change_status(num, status):
    data = pandas.read_excel("storage.xlsx", index_col=False)

    for i in range(len(data["tgid"])):
        if int(data["num"][i]) == int(num):
            data["status"][i] = status
            break
    data.to_excel("storage.xlsx", index=False)