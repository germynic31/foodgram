from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer
from rest_framework import serializers

from foods.models import (
    Tag, Recipe, Ingredient, Follow, Favorite, Cart, IngredientRecipe
)
from .fields import Base64ImageField


User = get_user_model()


class UserReadSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj):
        current_user = self.context['request'].user
        if not current_user.is_anonymous:
            return Follow.objects.filter(
                user=current_user,
                following=obj
            ).exists()
        return False


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientRecipeSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )
    name = serializers.ReadOnlyField(
        source='ingredient.name'
    )
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeReadSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True)
    ingredients = IngredientRecipeSerializer(many=True, source='recipes')
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = UserReadSerializer()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart', 'name', 'image',
            'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        current_user = self.context.get('request').user
        if current_user.is_anonymous:
            return False
        return Favorite.objects.filter(
            user=current_user, recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        current_user = self.context.get('request').user
        if current_user.is_anonymous:
            return False
        return Cart.objects.filter(
            user=current_user, recipe=obj
        ).exists()


class RecipeWriteSerializer(serializers.ModelSerializer):
    ingredients = IngredientRecipeSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'ingredients', 'tags', 'image', 'name',
            'text', 'cooking_time'
        )
        read_only_fields = ('author', 'created', 'id')

    def to_representation(self, instance):
        full_response = RecipeReadSerializer(
            instance,
            context={
                'request': self.context['request'],
            }
        )
        return full_response.data

    def validate(self, data):
        try:
            ingredients = data['ingredients']
            tags = data['tags']
        except KeyError:
            raise serializers.ValidationError('Нет ингредиентов или тегов!')
        if not ingredients or not tags:
            raise serializers.ValidationError('Нет ингредиентов или тегов!')

        unique_ingredients = []
        unique_tags = []
        for ingredient in ingredients:
            try:
                ingredient_object = Ingredient.objects.get(
                    id=ingredient.get('ingredient').id
                )
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(
                    'Указаны несуществующие ингредиенты!'
                )
            if ingredient_object in unique_ingredients:
                raise serializers.ValidationError('Ингредиенты не уникальны!')
            unique_ingredients.append(ingredient_object)
        for tag in tags:
            tag_object = get_object_or_404(
                Tag,
                id=tag.id,
            )
            if tag_object in unique_tags:
                raise serializers.ValidationError('Теги не уникальны!')
            unique_tags.append(tag_object)

        return super().validate(data)

    @staticmethod
    def create_ingredient_recipe(ingredients, recipe):
        validated_ingredients = []
        for i in ingredients:
            obj = IngredientRecipe(
                recipe=recipe,
                amount=i['amount'],
                ingredient_id=i['ingredient'].id
            )
            validated_ingredients.append(obj)
        IngredientRecipe.objects.bulk_create(validated_ingredients)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        recipe = super().create(validated_data)
        self.create_ingredient_recipe(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        instance.ingredients.clear()
        instance.tags.clear()
        self.create_ingredient_recipe(ingredients, instance)
        return super().update(instance, validated_data)


class FavoriteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Favorite
        fields = ('user', 'recipe')


class RecipeForUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FollowSerializer(UserReadSerializer):
    recipes_count = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta(UserReadSerializer.Meta):
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'recipes', 'recipes_count',
            'avatar',
        )
        read_only_fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'recipes', 'recipes_count',
            'avatar',
        )

    def validate(self, data):
        following_email = data['email']
        current_user = self.context.get('request').user
        if Follow.objects.filter(
                user=current_user, following__email=following_email
        ).exists():
            raise serializers.ValidationError('Вы уже подписаны!')
        if current_user.email == following_email:
            raise serializers.ValidationError('Нельзя подписаться на себя!')
        return data

    def get_is_subscribed(self, obj):
        current_user = self.context['request'].user
        if not current_user.is_anonymous:
            return Follow.objects.filter(
                user=current_user,
                following=obj
            ).exists()
        return False

    def get_recipes_count(self, obj):
        try:
            return Recipe.objects.filter(
                author=obj.following
            ).count()
        except AttributeError:
            return Recipe.objects.filter(
                author=obj
            ).count()

    def get_recipes(self, obj):
        recipes_limit = int(
            self.context.get('request').GET.get('recipes_limit', 6)
        )
        try:
            recipes = Recipe.objects.filter(
                author=obj.following
            )[:recipes_limit]
        except AttributeError:
            recipes = Recipe.objects.filter(author=obj)[:recipes_limit]
        return RecipeForUserSerializer(recipes, many=True).data


class FollowListSerializer(FollowSerializer):
    email = serializers.CharField(source='following.email')
    id = serializers.IntegerField(source='following.id')
    username = serializers.CharField(source='following.username')
    first_name = serializers.CharField(source='following.first_name')
    last_name = serializers.CharField(source='following.last_name')
    avatar = serializers.CharField(source='following.avatar')

    class Meta:
        model = Follow
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'recipes', 'recipes_count', 'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, obj):
        current_user = self.context['request'].user
        if not current_user.is_anonymous:
            return Follow.objects.filter(
                user=current_user,
                following=obj.following
            ).exists()
        return False


class DjoserUserCreateSerializer(UserCreateSerializer):
    password = serializers.CharField(
        style={"input_type": "password"},
        write_only=True,
        max_length=150
    )


class UserUpdateAvatar(UserReadSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)
