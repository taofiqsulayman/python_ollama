import csv

def process_csv(file_obj):
    file_obj.seek(0)
    reader = csv.reader(file_obj.read().decode('utf-8').splitlines())
    return "\n".join([",".join(row) for row in reader])