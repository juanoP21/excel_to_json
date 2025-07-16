from django.urls import path
from . import views

urlpatterns = [
    # Authentication endpoints
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('usuario/<int:id_usuario>/', views.UsuarioDetailView.as_view(), name='usuario-detail'),
    path('usuarios/lista_proyecto/<int:proyecto>/', views.UsuariosListaProyectoView.as_view(), name='usuarios-lista-proyecto'),
    path('usuarios/', views.UsuariosListView.as_view(), name='usuarios-list'),
    
    # Proyecto endpoints
    path('proyecto/nuevo/', views.ProyectoNuevoView.as_view(), name='proyecto-nuevo'),
    path('proyecto/lista/', views.ProyectoListaView.as_view(), name='proyecto-lista'),
    path('proyecto/editar/', views.ProyectoEditarView.as_view(), name='proyecto-editar'),
    path('proyecto/eliminar/', views.ProyectoEliminarView.as_view(), name='proyecto-eliminar'),
    
    # Vehiculo endpoints
    path('vehiculo/nuevo/', views.VehiculoNuevoView.as_view(), name='vehiculo-nuevo'),
    
    # Tipo Usuario endpoints
    path('tipo_usuarios/nuevo/', views.TipoUsuarioNuevoView.as_view(), name='tipo-usuario-nuevo'),
    path('tipo_usuarios/lista/', views.TipoUsuarioListaView.as_view(), name='tipo-usuario-lista'),
    path('tipo_usuarios/editar/', views.TipoUsuarioEditarView.as_view(), name='tipo-usuario-editar'),
    path('tipo_usuarios/eliminar/', views.TipoUsuarioEliminarView.as_view(), name='tipo-usuario-eliminar'),
    
    # Tipo Documento endpoints
    path('tipo_documento/nuevo/', views.TipoDocumentoNuevoView.as_view(), name='tipo-documento-nuevo'),
    path('tipo_documento/lista_activos/', views.TipoDocumentoListaActivosView.as_view(), name='tipo-documento-lista-activos'),
    path('tipo_documento/lista/', views.TipoDocumentoListaView.as_view(), name='tipo-documento-lista'),
    path('tipo_documento/editar/', views.TipoDocumentoEditarView.as_view(), name='tipo-documento-editar'),
    path('tipo_documento/eliminar/', views.TipoDocumentoEliminarView.as_view(), name='tipo-documento-eliminar'),
]
