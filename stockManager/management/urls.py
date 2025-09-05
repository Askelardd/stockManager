from django.urls import path # type: ignore
from django.conf.urls.static import static # type: ignore

from stockManager import settings # type: ignore
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/<int:user_id>/', views.login_view, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('listar_pos/', views.listar_pos, name='listar_pos'),
    path('po/<int:po_id>/adicionar/', views.adicionarMaisde1Po, name='adicionar_po'),
    path('po/<int:po_id>/remover/', views.removerPo, name='remover_po'),
    path('listar_update_pos/', views.listar_updates, name='listar_update_pos'),
    path('listar_fios/', views.listar_fios, name='listar_fios'),
    path('fio/<int:fio_id>/adicionar/', views.adicionarMaisde1Fio, name='adicionar_fio'),
    path('fio/<int:fio_id>/remover/', views.removerFio, name='remover_fio'),
    path('listar_update_fios/', views.listar_updates_fios, name='listar_update_fios'),
    path('po/saidas/', views.filtrar_po_saidas, name='filtrar_po_saidas'),
    path('po/entradas/', views.filtrar_po_entradas, name='filtrar_po_entradas'),
    path('fios/trafilar/', views.trafilar_fio, name='trafilar_fio'),
    path('fios/criar-rapido/', views.criar_fio_rapido, name='criar_fio_rapido'),
    path('trafilar/historico/', views.historico_trefilagens, name='historico_trefilagens'),
    path('fios/historico/', views.historico_fios, name='historico_fios'),
    path('novo_fio/', views.novo_fio, name='novo_fio'),
    path('listar_stock/', views.listar_stock, name='listar_stock'),
    path('stock/<int:stock_id>/adicionar/', views.adicionarStock, name='adicionar_stock'),
    path('stock/<int:stock_id>/remover/', views.removerStock, name='remover_stock'),
    path("po/historico/", views.historico_po, name="historico_po"),
    path("stock/historico/", views.historico_stock, name="historico_stock"),

    path("listar_agulhas/", views.listar_agulhas, name="listar_agulhas"),
    path("adicionar_agulha/<int:agulha_id>/", views.adicionar_agulha, name="adicionar_agulha"),
    path("remover_agulha/<int:agulha_id>/", views.remover_agulha, name="remover_agulha"),
    path("agulha/historico/", views.historico_agulhas, name="historico_agulhas"),
    path("menu_agulhas/", views.menu_agulhas, name="menu_agulhas"),
    path("nova_agulha/", views.nova_agulha, name="nova_agulha"),

    path("novo_stock/", views.novo_stock, name="novo_stock"),
    path("menu_stock/", views.menu_stock, name="menu_stock"),
    path("menu_fio/", views.menu_fio, name="menu_fio"),
    path("menu_po/", views.menu_po, name="menu_po"),
    path("main_menu/", views.main_menu, name="main_menu"),

]