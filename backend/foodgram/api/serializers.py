from django.contrib.auth import get_user_model
from django.forms import CharField, ValidationError
from djoser.serializers import (UserCreateSerializer, UserSerializer,
                                PasswordSerializer)
from recipes.models import (Recipe, Tag, Ingredient, RecipeIngredient,
                            Favorite, ShoppingCart)
from rest_framework.serializers import (ModelSerializer, IntegerField,
                                        ReadOnlyField,
                                        PrimaryKeyRelatedField,
                                        SerializerMethodField)

from drf_extra_fields.fields import Base64ImageField
from users.models import Follow
from django.db import transaction


User = get_user_model()


class ChangePasswordSerializer(PasswordSerializer):
    new_password = CharField(required=True)

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()


class CustomUserSerializer(UserSerializer):
    is_subscribed = SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
        )

    def get_is_subscribed(self, obj):
        return Follow.objects.exists()


class CustomUserCreateSerializer(UserCreateSerializer):

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'password')


class FollowSerializer(ModelSerializer):
    email = ReadOnlyField(source='author.email')
    id = ReadOnlyField(source='author.id')
    username = ReadOnlyField(source='author.username')
    first_name = ReadOnlyField(source='author.first_name')
    last_name = ReadOnlyField(source='author.last_name')
    is_subscribed = SerializerMethodField()
    recipes = SerializerMethodField()
    recipes_count = SerializerMethodField()

    class Meta:
        model = Follow
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'recipes',
                  'recipes_count')

    def get_is_subscribed(self, obj):
        return obj.author.following.filter(
            user=obj.user, author=obj.author).exists()

    def get_recipes_count(self, obj):
        return obj.author.recipes.filter(
            author=obj.author).count()

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        queryset = obj.author.recipes.all()
        if limit:
            queryset = queryset[:int(limit)]
        return RecipeShortShowSerializer(queryset, many=True).data


class TagSerializer(ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class IngredientSerializer(ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(ModelSerializer):
    id = IntegerField(source='ingredient.id')
    name = ReadOnlyField(source='ingredient.name')
    measurement_unit = ReadOnlyField(
        source='ingredient.measurement_unit')

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')

    def get_ingredient(self, obj):
        return obj.ingredient.first()

    def to_representation(self, instance):
        ingredient = self.get_ingredient(instance)
        return super().to_representation(ingredient)


class RecipeReadSerializer(ModelSerializer):
    tags = TagSerializer(read_only=True, many=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(source='recipeingredient_set',
                                             read_only=True, many=True)
    is_favorited = SerializerMethodField()
    is_in_shopping_cart = SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = '__all__'

    def get_is_favorited(self, obj):

        return obj.favorite.exists()

    def get_is_in_shopping_cart(self, obj):

        return obj.shoppingcart.exists()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        data['recipes'] = RecipeShortShowSerializer(
            instance.author.recipes.all()[:request.GET.get('recipes_limit')],
            many=True,
            context=self.context
        ).data
        return data


class RecipeShortShowSerializer(ModelSerializer):
    image = Base64ImageField(read_only=True)
    name = ReadOnlyField()
    cooking_time = ReadOnlyField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeSerializer(ModelSerializer):
    ingredients = RecipeIngredientSerializer(many=True)
    tags = PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all())
    author = CustomUserSerializer(read_only=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('ingredients', 'tags', 'image', 'name', 'text',
                  'cooking_time', 'author')

    def create_ingredients_for_recipe(self, recipe, ingredietns):
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(recipe=recipe,
                             ingredient_id=ingredient.get(
                                            ('ingredient')).get('id'),
                             amount=ingredient.get('amount'),)
            for ingredient in ingredietns])

    def validate_ingredient(self, data):
        ingredients_list = []
        for ingredient in data.get('recipeingredients'):
            if int(ingredient.get('amount')) <= 0:
                raise ValidationError(
                    'Количество не может быть меньше 1'
                )
            ingredients_list.append(ingredient.get('id'))
        if len(set(ingredients_list)) != len(ingredients_list):
            raise ValidationError(
                'Ингредиенты не должны повторяться!'
            )
        return data

    def validate_tags(self, tags):
        if not tags:
            raise ValidationError('Укажите тэг!')
        return tags

    def validate_cooking_time(self, cooking_time):
        if int(cooking_time) == 0:
            raise ValidationError('Время приготовления не может быть равно 0!')
        return cooking_time

    @transaction.atomic()
    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients_for_recipe(recipe, ingredients_data)
        return recipe

    @transaction.atomic()
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        ingredietns = validated_data.pop('ingredients')
        instance.tags.clear()
        RecipeIngredient.objects.filter(recipe=instance).delete()
        instance.tags.set(tags)
        self.create_ingredients_for_recipe(instance, ingredietns)
        return super().update(instance, validated_data)


class FavoriteSerializer(ModelSerializer):

    class Meta:
        model = Favorite
        fields = ('user', 'recipe')

    def validate_user(self, user):
        recipe = self.initial_data.get('recipe')
        if user.favorite.filter(recipe=recipe).exists():
            raise ValidationError('Рецепт уже был добавлен в избранное')

        return user


class ShoppingCartSerializer(ModelSerializer):

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def validate_user(self, user):
        recipe = self.initial_data.get('recipe')
        if user.shoppingcart.filter(recipe=recipe).exists():
            raise ValidationError('Рецепт уже был добавлен в корзину')
        return user
