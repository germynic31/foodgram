from django.contrib.auth.models import AnonymousUser
from django_filters import (
    CharFilter, FilterSet, NumberFilter
)

from foods.models import Recipe, Ingredient


class IngredientFilter(FilterSet):
    name = CharFilter(field_name='name', lookup_expr='startswith')

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(FilterSet):
    tags = CharFilter(
        field_name='tags__slug', lookup_expr='icontains', method='filter_tags'
    )
    author = CharFilter(field_name='author__id', lookup_expr='icontains')
    is_favorited = NumberFilter(method='filter_is_favorited')
    is_in_shopping_cart = NumberFilter(method='filter_is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ('tags', 'author', 'is_favorited', 'is_in_shopping_cart')

    def filter_tags(self, queryset, name, value):
        tags_params = self.request.GET.getlist('tags')
        if tags_params:
            return queryset.filter(tags__slug__in=tags_params).distinct()
        else:
            return queryset

    def filter_is_favorited(self, queryset, name, value):
        current_user = self.request.user
        if not isinstance(current_user, AnonymousUser) and value:
            return queryset.filter(favorites__user=current_user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        current_user = self.request.user
        if not isinstance(current_user, AnonymousUser) and value:
            return queryset.filter(cart__user=current_user)
        return queryset
