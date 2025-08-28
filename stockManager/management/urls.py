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

    
]