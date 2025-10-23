from django.contrib import admin
from .models import FioTransformacao, FioTransformacaoItem, Fornecedor, Po, Fios, CategoriaProduto, updatePo, updateFios, poSaidas, stockMaquinas
from .models import poEntradas, Stock, StockEntradas, StockSaidas, UpdateStock, Agulhas, AgulhasEntradas, AgulhasSaidas, UpdateAgulhas, FioUsado

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

@admin.register(FioUsado)
class FioUsadoAdmin(admin.ModelAdmin):
    list_display = ('fio', 'size', 'weight', 'material', 'quantidade_usada', 'data_uso', 'user')
    search_fields = ('fio__size', 'material', 'user__username')
    list_filter = ('data_uso', 'material', 'user')

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

@admin.register(FioTransformacao)
class FioTransformacaoAdmin(admin.ModelAdmin):
    list_display = ('origem', 'total_transferido', 'peso_origem_antes', 'peso_origem_depois', 'user', 'created_at')
    search_fields = ('origem__size', 'user__username')
    list_filter = ('created_at', 'user')

@admin.register(FioTransformacaoItem)
class FioTransformacaoItemAdmin(admin.ModelAdmin):
    list_display = ('transformacao', 'destino', 'peso_adicionado')
    search_fields = ('destino__size', 'transformacao__origem__size')
    list_filter = ('transformacao__created_at',)

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'min_stock', 'fornecedor', 'date_added', 'updated_at')
    search_fields = ('product',)
    list_filter = ('fornecedor', 'date_added', 'updated_at')

@admin.register(StockEntradas)
class StockEntradasAdmin(admin.ModelAdmin):
    list_display = ('stock', 'quantity_added', 'date_added', 'user', 'descricao')
    search_fields = ('stock__product', 'user__username')
    list_filter = ('date_added', 'user')

@admin.register(StockSaidas)
class StockSaidasAdmin(admin.ModelAdmin):
    list_display = ('stock', 'quantity_removed', 'date_removed', 'user', 'descricao')
    search_fields = ('stock__product', 'user__username')
    list_filter = ('date_removed', 'user')

@admin.register(CategoriaProduto)
class categoriaProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'descricao')
    search_fields = ('nome',)

@admin.register(UpdateStock)
class UpdateStockAdmin(admin.ModelAdmin):
    list_display = ('stock', 'previous_quantity', 'new_quantity', 'date_updated', 'action', 'user')
    search_fields = ('stock__product', 'user__username')
    list_filter = ('action', 'user', 'date_updated')

@admin.register(Agulhas)
class AgulhasAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'tamanho', 'quantidade', 'fornecedor', 'user')
    search_fields = ('tipo', 'fornecedor__nome')
    list_filter = ('fornecedor',)

@admin.register(AgulhasEntradas)
class AgulhasEntradasAdmin(admin.ModelAdmin):
    list_display = ('agulha', 'quantity_added', 'date_added', 'user')
    search_fields = ('agulha__tipo', 'user__username')
    list_filter = ('date_added', 'user')

@admin.register(AgulhasSaidas)
class AgulhasSaidasAdmin(admin.ModelAdmin):
    list_display = ('agulha', 'quantity_removed', 'date_removed', 'user')
    search_fields = ('agulha__tipo', 'user__username')
    list_filter = ('date_removed', 'user')

@admin.register(UpdateAgulhas)
class UpdateAgulhasAdmin(admin.ModelAdmin):
    list_display = ('agulha', 'previous_quantity', 'new_quantity', 'date_updated', 'action', 'user')
    search_fields = ('agulha__tipo', 'user__username')
    list_filter = ('action', 'date_updated', 'user')

@admin.register(stockMaquinas)
class stockMaquinasAdmin(admin.ModelAdmin):
    list_display = (
        'machine_number', 'production_equipment', 'model', 'purpose', 
        'defined_location', 'serial_number', 'manual', 'certificado_ce', 
        'fornecedor', 'contact', 'manutenance_date', 'edited_at', 'user'
    )
    search_fields = ('machine_number', 'model', 'serial_number', 'purpose', 'fornecedor__nome', 'user__username')
    list_filter = ('defined_location', 'manual', 'certificado_ce', 'fornecedor', 'manutenance_date', 'edited_at', 'user')
