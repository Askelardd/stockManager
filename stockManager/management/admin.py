from django.contrib import admin
from .models import Fornecedor, Po, Fios, updatePo, updateFios, poSaidas, poEntradas

# Register your models here.
@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ref_fornecedor', 'email', 'telefone')
    search_fields = ('nome', 'ref_fornecedor', 'email')

@admin.register(Po)
class PoAdmin(admin.ModelAdmin):
    list_display = ('product', 'reference', 'min_stock', 'quantity', 'fornecedor', 'date_added', 'updated_at')
    search_fields = ('product', 'reference')
    list_filter = ('fornecedor', 'date_added', 'updated_at')

@admin.register(Fios)
class FiosAdmin(admin.ModelAdmin):
    list_display = ('size', 'weight', 'quantity', 'material', 'min_stock', 'fornecedor', 'date_added', 'updated_at')
    search_fields = ('size', 'material')
    list_filter = ('fornecedor', 'material', 'date_added', 'updated_at')

@admin.register(updateFios)
class updateFiosAdmin(admin.ModelAdmin):
    list_display = ('fio', 'previous_quantity', 'new_quantity', 'date_updated', 'user')
    search_fields = ('fio__size', 'user__username')
    list_filter = ('date_updated', 'user')

@admin.register(updatePo)
class updatePoAdmin(admin.ModelAdmin):
    list_display = ('po', 'action', 'previous_quantity', 'new_quantity', 'date_updated', 'user')
    search_fields = ('po__product', 'user__username')
    list_filter = ('action', 'user', 'date_updated')

@admin.register(poSaidas)
class poSaidasAdmin(admin.ModelAdmin):
    list_display = ('po', 'user', 'quantity_used')  # Removed 'date_added'
    search_fields = ('po__product', 'user__username')
    list_filter = ('user',)  # Removed 'date_added'

@admin.register(poEntradas)
class poEntradasAdmin(admin.ModelAdmin):
    list_display = ('po', 'user', 'quantity_added')  # Removed 'date_added'
    search_fields = ('po__product', 'user__username')
    list_filter = ('user',)  # Removed 'date_added'