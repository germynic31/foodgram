from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
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

    @staticmethod
    def validate_and_create_object(request, class_, pk):
        current_user = request.user
        if not Recipe.objects.filter(id=pk).exists():
            return Response(
                {'errors': 'Рецепт не существует!'},
                status=status.HTTP_404_NOT_FOUND
            )
        if class_.objects.filter(user=current_user, recipe=pk).exists():
            return Response(
                {'errors': 'Рецепт уже добавлен!'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = RecipeForUserSerializer(
            Recipe.objects.get(id=pk), context={'request': request}
        )
        class_.objects.create(
            user=current_user, recipe=Recipe.objects.get(id=pk)
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def validate_and_delete_object(request, class_, pk):
        current_user = request.user
        recipe = get_object_or_404(Recipe, id=int(pk))
        try:
            class_.objects.get(user=current_user, recipe=recipe).delete()
        except class_.DoesNotExist:
            return Response(
                {'errors': 'Вы не добавляли этот ингредиент в корзину'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def shopping_cart(self, request, pk=None):
        return self.validate_and_create_object(
            request, Cart, pk
        )

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        return self.validate_and_delete_object(
            request, Cart, pk
        )

    @action(detail=True, methods=['post'])
    def favorite(self, request, pk=None):
        return self.validate_and_create_object(
            request, Favorite, pk
        )

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        return self.validate_and_delete_object(
            request, Favorite, pk
        )

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
            return Response(
                {'errors': 'У вас пустая корзина!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        ings = IngredientRecipe.objects.filter(
            recipe__cart__user=current_user
        ).values('ingredient__name', 'ingredient__measurement_unit').annotate(
            sum_amount=Sum('amount')
        )
        for ing in ings:
            shopping_cart_list += (
                f'{ing["ingredient__name"]} - '
                f'{ing["sum_amount"]}'
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
            domain = settings.ALLOWED_HOSTS[0]
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
            return Response(
                {'errors': 'Нельзя подписаться на себя!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if Follow.objects.filter(
                user=current_user, following=following
        ).exists():
            return Response(
                {'errors': 'Вы уже подписаны!'},
                status=status.HTTP_400_BAD_REQUEST
            )
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
        obj = get_object_or_404(User, email=current_user)
        serializer = UserReadSerializer(obj, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['put'], url_path='me/avatar')
    def avatar(self, request):
        current_user = request.user
        serializer = UserUpdateAvatar(
            current_user, data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        current_user = request.user
        current_user.avatar = None
        current_user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
