from django.urls import path # type: ignore
from django.conf.urls.static import static # type: ignore

from stockManager import settings # type: ignore
from . import views

from management import views as management_views # type: ignore


urlpatterns = [
    # Menus
    path("main_menu/", views.main_menu, name="main_menu"),
    path("menu_stock/", views.menu_stock, name="menu_stock"),
    path("menu_fio/", views.menu_fio, name="menu_fio"),
    path("menu_po/", views.menu_po, name="menu_po"),
    path("menu_agulhas/", views.menu_agulhas, name="menu_agulhas"),
    path("menu_fornecedor/", views.menu_fornecedor, name="menu_fornecedor"),
    path("menu_maquinas/", views.menu_maquinas, name="menu_maquinas"),

    # Fios
    path('listar_fios/', views.listar_fios, name='listar_fios'),
    path('fio/<int:fio_id>/adicionar/', views.adicionarMaisde1Fio, name='adicionar_fio'),
    path('fio/<int:fio_id>/editar/', views.editar_fio, name='editar_fio'),
    path('fio/<int:fio_id>/retirar/', views.retirar_fio, name='retirar_fio'),
    path('fios/trafilar/', views.trafilar_fio, name='trafilar_fio'),
    path('fios/criar-rapido/', views.criar_fio_rapido, name='criar_fio_rapido'),
    path('fios/historico/', views.historico_fios, name='historico_fios'),
    path('novo_fio/', views.novo_fio, name='novo_fio'),
    path('listar_fiousado/', views.listar_fiousado, name='listar_fiousado'),
    path('deletar_fiousado/<int:id>/', views.deletar_fiousado, name='deletar_fiousado'),

    # Trefilagem
    path('trafilar/historico/', views.historico_trefilagens, name='historico_trefilagens'),

    # PO
    path('listar_pos/', views.listar_pos, name='listar_pos'),
    path('po/<int:po_id>/adicionar/', views.adicionarMaisde1Po, name='adicionar_po'),
    path('po/<int:po_id>/remover/', views.removerPo, name='remover_po'),
    path("po/historico/", views.historico_po, name="historico_po"),

    # Stock
    path('listar_stock/', views.listar_stock, name='listar_stock'),
    path('stock/<int:stock_id>/adicionar/', views.adicionarStock, name='adicionar_stock'),
    path('stock/<int:stock_id>/remover/', views.removerStock, name='remover_stock'),
    path("editar_stock/<int:stock_id>/", views.editar_stock, name="editar_stock"),
    path("delete_stock/<int:stock_id>/", views.delete_stock, name="delete_stock"),
    path("novo_stock/", views.novo_stock, name="novo_stock"),
    path("stock/historico/", views.historico_stock, name="historico_stock"),

    # Agulhas
    path("listar_agulhas/", views.listar_agulhas, name="listar_agulhas"),
    path("adicionar_agulha/<int:agulha_id>/", views.adicionar_agulha, name="adicionar_agulha"),
    path("remover_agulha/<int:agulha_id>/", views.remover_agulha, name="remover_agulha"),
    path("agulha/historico/", views.historico_agulhas, name="historico_agulhas"),
    path("nova_agulha/", views.nova_agulha, name="nova_agulha"),

    # Maquinas
    path('maquinas/', views.listar_e_adicionar_maquinas, name='listar_adicionar_maquinas'),
    path('editar_maquina/<int:maquina_id>/', views.editar_maquina, name='editar_maquina'),
    path('deletar_maquina/<int:maquina_id>/', views.deletar_maquina, name='deletar_maquina'),

    # Fornecedores
    path("criar_fornecedor/", views.criar_fornecedor, name="criar_fornecedor"),
    path("listar_fornecedores/", views.listar_fornecedores, name="listar_fornecedores"),
    path("editar_fornecedor/<int:fornecedor_id>/", views.editar_fornecedor, name="editar_fornecedor"),
    path("deletar_fornecedor/<int:fornecedor_id>/", views.deletar_fornecedor, name="deletar_fornecedor"),

    # Autenticação
    path('', views.index, name='index'),
    path('login/<int:user_id>/', views.login_view, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Erros
    path('403/', views.error_403, name='error_403'),

    #Stock pages
    path('stock_overview/', views.stock_overview, name='stock_overview'),
]
handler404 = management_views.error_404