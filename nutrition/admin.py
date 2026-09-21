from django.contrib import admin

from .models import Food, MealItem, MealLog


class MealItemInline(admin.TabularInline):
    model = MealItem
    extra = 0


@admin.register(MealLog)
class MealLogAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "meal_type", "source"]
    list_filter = ["meal_type", "source", "date"]
    inlines = [MealItemInline]


@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = ["name", "brand", "calories", "source"]
    list_filter = ["source"]
    search_fields = ["name", "brand"]
