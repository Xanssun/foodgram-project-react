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
                try:
                    Ingredient.objects.get_or_create(**ing)
                except Exception:
                    print(f'Ингрединет {ing} есть в базе')
