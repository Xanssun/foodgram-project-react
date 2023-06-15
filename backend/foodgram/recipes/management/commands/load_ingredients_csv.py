import csv
from django.core.management import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    help = "Loads data from ingredients.csv"

    def handle(self, *args, **options):
        file_name = 'recipes/data/ingredients.csv'
        with open(file_name, 'r', encoding='utf-8') as file:
            file = csv.reader(file)
            for ing in file:
                name, measurement_unit = ing
                try:
                    Ingredient.objects.get_or_create(
                        name=name,
                        measurement_unit=measurement_unit
                    )
                except Exception:
                    print(f'Ингрединет {ing} есть в базе')
