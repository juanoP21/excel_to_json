from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('usuario/<int:id_usuario>/', views.UsuarioDetailView.as_view(), name='usuario-detail'),
    path('usuarios/lista_proyecto/<int:proyecto>/', views.UsuariosListaProyectoView.as_view(), name='usuarios-lista-proyecto'),
    path('usuarios/', views.UsuariosListView.as_view(), name='usuarios-list'),
]
