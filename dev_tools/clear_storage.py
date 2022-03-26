import csv

with open('storage.csv', 'w', encoding='utf-8') as csvfile:
    fieldnames = ['tgid', 'num', 'fio', 'time', 'longitude', 'latitude', 'status']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()