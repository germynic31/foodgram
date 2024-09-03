import os

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response
from djoser.views import UserViewSet as DjoserViewSet

from foods.models import (
    Tag, Ingredient, Recipe, Follow, Cart, Favorite, IngredientRecipe
)
from .paginators import RecipeUserPaginator
from .permissions import AuthorOrReadOnlyPermission
from .filters import RecipeFilter, IngredientFilter
from .serializers import (
    TagSerializer, IngredientSerializer, RecipeReadSerializer,
    RecipeWriteSerializer, UserReadSerializer, FollowSerializer,
    RecipeForUserSerializer, FollowListSerializer, DjoserUserCreateSerializer,
    UserUpdateAvatar
)


User = get_user_model()


class TagViewSet(
    viewsets.ReadOnlyModelViewSet
):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(
    viewsets.ReadOnlyModelViewSet
):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    filterset_class = RecipeFilter
    pagination_class = RecipeUserPaginator

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_permissions(self):
        if self.action == 'download_shopping_cart':
            return (IsAuthenticated(),)
        if self.action not in ['retrieve', 'list']:
            return (AuthorOrReadOnlyPermission(),)
        return (AllowAny(),)

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeWriteSerializer

    @action(detail=True, methods=['post'])
    def shopping_cart(self, request, pk=None):
        current_user = request.user
        if not Recipe.objects.filter(id=pk).exists():
            return Response(
                {'errors': 'Рецепт не существует!'},
                status=status.HTTP_404_NOT_FOUND
            )
        if Cart.objects.filter(user=current_user, recipe=pk).exists():
            return Response(
                {'errors': 'Рецепт уже добавлен!'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = RecipeForUserSerializer(
            Recipe.objects.get(id=pk), context={'request': request}
        )
        Cart.objects.create(
            user=current_user, recipe=Recipe.objects.get(id=pk)
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        current_user = request.user
        try:
            recipe = Recipe.objects.get(id=int(pk))
        except Recipe.DoesNotExist:
            return Response(
                {'errors': 'Рецепт не существует!'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            Cart.objects.get(user=current_user, recipe=recipe).delete()
        except Cart.DoesNotExist:
            return Response(
                {'errors': 'Вы не добавляли этот ингредиент в корзину'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def favorite(self, request, pk=None):
        current_user = request.user
        try:
            recipe = Recipe.objects.get(id=int(pk))
        except Recipe.DoesNotExist:
            return Response(
                {'errors': 'Рецепт не существует!'},
                status=status.HTTP_404_NOT_FOUND
            )
        if Favorite.objects.filter(user=current_user, recipe=recipe).exists():
            return Response(
                {'errors': 'Рецепт уже добавлен!'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = RecipeForUserSerializer(
            recipe, context={'request': request}
        )
        Favorite.objects.create(user=current_user, recipe=recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        current_user = request.user
        try:
            recipe = Recipe.objects.get(id=int(pk))
        except Recipe.DoesNotExist:
            return Response(
                {'errors': 'Рецепт не существует!'},
                status=status.HTTP_404_NOT_FOUND
            )
        try:
            Favorite.objects.get(user=current_user, recipe=recipe).delete()
        except Favorite.DoesNotExist:
            return Response(
                {'errors': 'Вы не добавляли этот ингредиент в избранные'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False, methods=['get']
    )
    def download_shopping_cart(self, request):
        current_user = request.user
        shopping_cart_list = (
            f'Список покупок пользователя:'
            f' {current_user.username}\n'
        )
        if not current_user.cart.exists():
            raise serializers.ValidationError(
                'У вас пустая корзина!'
            )
        ings = IngredientRecipe.objects.filter(
            recipe__cart__user=current_user
        ).values('ingredient__name', 'ingredient__measurement_unit').annotate(
            amount=Sum('amount')
        )
        for ing in ings:
            shopping_cart_list += (
                f'{ing["ingredient__name"]} - '
                f'{ing["amount"]}'
                f'{ing["ingredient__measurement_unit"]}'
                f'\n'
            )
        filename = f'{current_user.username} shopping cart'
        response = HttpResponse(shopping_cart_list, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="{0}"'.format(filename)
        )
        return response

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        if Recipe.objects.filter(pk=pk).exists():
            domain = os.getenv(
                'ALLOWED_HOSTS', '127.0.0.1, localhost'
            ).split(', ')[0]
            link = f'{domain}/recipes/{pk}/'
            return Response({'short-link': link})
        return Response(
            {'errors': 'Рецепт не существует!'},
            status=status.HTTP_404_NOT_FOUND
        )


class UserViewSet(DjoserViewSet):
    pagination_class = RecipeUserPaginator

    def get_queryset(self):
        return User.objects.all()

    def get_serializer_class(self):
        if self.action in ['retrieve', 'list']:
            return UserReadSerializer
        if self.action == 'create':
            return DjoserUserCreateSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action in ['retrieve', 'list']:
            return [AllowAny()]
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        current_user = request.user
        followings = current_user.users.all()
        subs = self.paginate_queryset(followings)
        serializer = FollowListSerializer(
            subs, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'])
    def subscribe(self, request, id=None):
        current_user = request.user
        following = get_object_or_404(User, id=int(id))
        if current_user == following:
            raise serializers.ValidationError('Нельзя подписаться на себя!')
        if Follow.objects.filter(
                user=current_user, following=following
        ).exists():
            raise serializers.ValidationError('Вы уже подписаны!')
        serializer = FollowSerializer(following, context={'request': request})
        Follow.objects.create(user=current_user, following=following)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id=None):
        current_user = request.user
        following = get_object_or_404(User, id=int(id))
        try:
            Follow.objects.get(user=current_user, following=following).delete()
        except Follow.DoesNotExist:
            raise serializers.ValidationError(
                'Вы не подписаны на данного пользователя'
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def me(self, request):
        current_user = request.user
        obj = User.objects.get(email=current_user)
        serializer = UserReadSerializer(obj, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['put'], url_path='me/avatar')
    def avatar(self, request):
        current_user = request.user
        serializer = UserUpdateAvatar(
            current_user, data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        current_user = User.objects.get(email=request.user.email)
        current_user.avatar = None
        current_user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
