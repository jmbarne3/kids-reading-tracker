from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ChildProfile, SocialAccount, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Reading Tracker', {'fields': ('role', 'parent', 'date_of_birth', 'avatar_url')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Reading Tracker', {'fields': ('role', 'date_of_birth')}),
    )


@admin.register(ChildProfile)
class ChildProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'date_of_birth', 'created_at')
    list_filter = ('parent',)
    search_fields = ('name', 'parent__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'provider_user_id', 'email')
    list_filter = ('provider',)
    search_fields = ('user__email', 'provider_user_id', 'email')
