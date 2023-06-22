from django_filters.rest_framework import FilterSet, filters

from recipes.models import Recipe, Tag


class AuthorAndTagFilter(FilterSet):

    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    is_favorited = filters.BooleanFilter(method='is_favorited_filter')
    is_in_shopping_cart = filters.BooleanFilter(
        method='is_in_shopping_cart_filter'
    )

    class Meta:
        model = Recipe
        fields = (
            'tags',
            'author',
            'is_favorited',
            'is_in_shopping_cart',
        )

    def is_favorited_filter(self, queryset, name, data):
        user = self.request.user
        if data and user.is_authenticated:
            return queryset.filter(favorite__user=user)
        return queryset

    def is_in_shopping_cart_filter(self, queryset, name, data):
        user = self.request.user
        if data and user.is_authenticated:
            return queryset.filter(shoppingcart__user=user)
        return queryset
