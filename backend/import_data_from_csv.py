import logging
import os
import csv

import django
from django.conf import settings
from django.db import IntegrityError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodgram_backend.settings')
if not settings.configured:
    django.setup()


def import_data_from_csv(file_path, model):
    debug_message = f'path: {file_path}, model: {model}'

    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames
        logging.debug('Началась загрузка csv файла\n' + debug_message)
        for row in reader:
            data = {}
            for column in columns:
                data[column] = row[column]
            try:
                # print(data)
                model.objects.create(**data)
            except IntegrityError:
                pass
        logging.debug('Завершилась загрузка csv файла\n' + debug_message)


def main():
    from foods.models import Ingredient

    default_path = 'foods/'
    file_names_models = [
        ('ingredients.csv', Ingredient),
    ]

    for file_name, model in file_names_models:
        full_path = os.path.join(default_path, file_name)
        import_data_from_csv(full_path, model)


if __name__ == '__main__':
    main()
