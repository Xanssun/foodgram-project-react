from django.contrib import admin

from recipes.models import (Recipe, Tag, Ingredient, RecipeIngredient,
                            Favorite, ShoppingCart)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'color',
        'slug'
    )
    search_fields = (
        'name',
        'color',
        'slug'
    )
    list_filter = (
        'name', 'slug'
    )


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'measurement_unit'
    )
    search_fields = (
        'name', 'measurement_unit'
    )
    list_filter = ('name',)


@admin.register(RecipeIngredient)
class RecipeAmauntIngredientAdmin(admin.ModelAdmin):
    list_display = ('amount', 'ingredient', 'recipe')


class RecipeIngredientAdmin(admin.StackedInline):
    model = RecipeIngredient
    autocomplete_fields = ('ingredient',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'count_favorites')
    list_filter = ('author', 'name', 'tags')
    inlines = (RecipeIngredientAdmin,)

    def count_favorites(self, obj):
        return obj.favorite.count()


admin.site.register(Favorite)
admin.site.register(ShoppingCart)
