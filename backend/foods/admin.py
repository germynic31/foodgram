from django.contrib import admin

from . import models


class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email')
    list_filter = ('username', 'email')
    search_fields = ('username', 'email')


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name',)
    list_filter = ('name',)
    search_fields = ('name',)


class IngredientRecipeInline(admin.TabularInline):
    model = models.IngredientRecipe
    min_num = 1


@admin.register(models.Recipe)
class RecipeAdmin(admin.ModelAdmin):
    inlines = [IngredientRecipeInline]
    list_display = ('name', 'author', 'favorites_count')
    list_filter = ('name', 'author', 'tags')
    search_fields = ('name', 'author', 'tags')


admin.site.register(models.Tag)
admin.site.register(models.Ingredient, IngredientAdmin)
admin.site.register(models.IngredientRecipe)
admin.site.register(models.Cart)
admin.site.register(models.Favorite)
admin.site.register(models.Follow)
admin.site.register(models.User, UserAdmin)
