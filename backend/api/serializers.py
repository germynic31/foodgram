import base64

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer
from rest_framework import serializers

from foods.models import (
    Tag, Recipe, Ingredient, Follow, Favorite, Cart, IngredientRecipe
)


User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


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
        if not isinstance(current_user, AnonymousUser):
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
        if isinstance(current_user, AnonymousUser):
            return False
        if Favorite.objects.filter(user=current_user, recipe=obj).exists():
            return True
        return False

    def get_is_in_shopping_cart(self, obj):
        current_user = self.context.get('request').user
        if isinstance(current_user, AnonymousUser):
            return False
        if Cart.objects.filter(user=current_user, recipe=obj).exists():
            return True
        return False


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
        for i in ingredients:
            try:
                ingredient = Ingredient.objects.get(id=i.get('ingredient').id)
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(
                    'Указаны несуществующие ингредиенты!'
                )
            if ingredient in unique_ingredients:
                raise serializers.ValidationError('Ингредиенты не уникальны!')
            unique_ingredients.append(ingredient)
        for i in tags:
            tag = get_object_or_404(
                Tag,
                id=i.id,
            )
            if tag in unique_tags:
                raise serializers.ValidationError('Теги не уникальны!')
            unique_tags.append(tag)

        return super().validate(data)

    @staticmethod
    def ingredient_recipe(ingredient, recipe):
        ings = []
        for i in ingredient:
            obj = IngredientRecipe(
                recipe=recipe,
                amount=i['amount'],
                ingredient_id=i['ingredient'].id
            )
            ings.append(obj)
        IngredientRecipe.objects.bulk_create(ings)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        recipe = super().create(validated_data)
        self.ingredient_recipe(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        instance.ingredients.clear()
        instance.tags.clear()
        self.ingredient_recipe(ingredients, instance)
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
        if not isinstance(current_user, AnonymousUser):
            return Follow.objects.filter(
                user=current_user,
                following=obj
            ).exists()
        return False

    def get_recipes_count(self, obj):
        if isinstance(obj, User) and not obj.is_anonymous:
            return Recipe.objects.filter(
                author=obj
            ).count()

        return Recipe.objects.filter(
            author=obj.following
        ).count()

    def get_recipes(self, obj):
        recipes_limit = int(
            self.context.get('request').GET.get('recipes_limit', 6)
        )

        if isinstance(obj, User) and not obj.is_anonymous:
            recipes = Recipe.objects.filter(author=obj)[:recipes_limit]
            return RecipeForUserSerializer(recipes, many=True).data

        recipes = Recipe.objects.filter(author=obj.following)[:recipes_limit]
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
        if not isinstance(current_user, AnonymousUser):
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
