from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from .paginations import LimitPageNumberPagination
from .serializers import (CustomUserCreateSerializer, CustomUserSerializer,
                          FollowSerializer, ChangePasswordSerializer,
                          TagSerializer,
                          IngredientSerializer, RecipeSerializer,
                          RecipeReadSerializer, FavoriteSerializer,
                          ShoppingCartSerializer)
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from .premissions import IsAuthorOrReadOnly
from .filters import AuthorAndTagFilter, IngredientFilter
from django.http.response import HttpResponse
from django.db.models import Sum
from rest_framework.permissions import IsAuthenticated

from recipes.models import (Recipe, Tag, Ingredient, RecipeIngredient,
                            Favorite, ShoppingCart)
from users.models import Follow
from django_filters.rest_framework import DjangoFilterBackend

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserCreateSerializer
    pagination_class = LimitPageNumberPagination

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return CustomUserSerializer
        return super().get_serializer_class()

    @action(detail=False, methods=('GET',),
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        user = self.request.user
        queryset = Follow.objects.filter(user=user)
        page = self.paginate_queryset(queryset)
        serializer = FollowSerializer(
            page, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        methods=('POST', 'DELETE',), detail=True,
        permission_classes=(IsAuthenticated,))
    def subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(User, id=id)
        if request.method == 'POST':
            serializer = FollowSerializer(
                Follow.objects.create(user=user, author=author),
                context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        Follow.objects.filter(user=user, author=author).delete()
        return Response('Успешная отписка', status=status.HTTP_204_NO_CONTENT)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        is_subscribed = False
        if request.user.is_authenticated:
            user = request.user
            author = instance
            is_subscribed = Follow.objects.filter(user=user,
                                                  author=author).exists()

        data = serializer.data
        data['is_subscribed'] = is_subscribed

        return Response(data)

    @action(
        methods=('POST',),
        detail=False,
        permission_classes=(IsAuthenticated,))
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data,
                                              context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Пороль изменен.'},
                        status=status.HTTP_200_OK)


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend, )
    filterset_class = IngredientFilter


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    filterset_class = AuthorAndTagFilter
    filter_backends = (DjangoFilterBackend, )
    permission_classes = [IsAuthorOrReadOnly]
    pagination_class = LimitPageNumberPagination

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = RecipeSerializer(instance)

        if request.method == 'PATCH':
            partial = kwargs.pop('partial', False)
            serializer = RecipeSerializer(instance, data=request.data,
                                          partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data,
                                         partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return RecipeReadSerializer
        return RecipeSerializer

    def add_obj(self, request, serializers, pk):
        data = {'user': request.user.id, 'recipe': pk}
        serializer = serializers(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete_obj(self, request, model, id):
        model_instance = model.objects.filter(user=request.user.id,
                                              recipe__id=id)
        if model_instance.exists():
            model_instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'error': 'Такого рецепта нет в списке.'
                         }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=('POST', 'DELETE',))
    def favorite(self, request, pk):
        if request.method == 'POST':
            return self.add_obj(request, FavoriteSerializer, pk)

        return self.delete_obj(request, Favorite, pk)

    @action(detail=True, methods=('POST', 'DELETE',))
    def shopping_cart(self, request, pk):
        if request.method == 'POST':
            return self.add_obj(request, ShoppingCartSerializer, pk)

        return self.delete_obj(request, ShoppingCart, pk)

    def create_shopping_cart(self, ingredients):
        shopping_list = 'Список покупок:'
        for ingredient in ingredients:
            shopping_list += (
                f"\n{ingredient['ingredient__name']} "
                f"({ingredient['ingredient__measurement_unit']}) - "
                f"{ingredient['ingredient_value']}")
        file = 'shopping_list.txt'
        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{file}.txt"'
        return response

    @action(detail=False, methods=('GET',))
    def download_shopping_cart(self, request):
        ingredients = RecipeIngredient.objects.filter(
            recipe__shoppingcart__user=request.user
        ).order_by('ingredient__name').values(
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(ingredient_value=Sum('amount'))
        return self.create_shopping_cart(ingredients)
