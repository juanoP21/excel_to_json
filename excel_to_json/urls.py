"""
URL configuration for excel_to_json project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from authapp import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/excel/', include('api.urls')),
    path('api/auth/', include('authapp.urls')),
    # Direct routes for frontend compatibility
    re_path(r'^register/?$', auth_views.RegisterView.as_view(), name='register-direct'),
    re_path(r'^login/?$', auth_views.LoginView.as_view(), name='login-direct'),
    re_path(r'^profile/?$', auth_views.ProfileView.as_view(), name='profile-direct'),
    re_path(r'^usuario/(?P<id_usuario>\d+)/?$', auth_views.UsuarioDetailView.as_view(), name='usuario-detail-direct'),
    re_path(r'^usuarios/lista_proyecto/(?P<proyecto>\d+)/?$', auth_views.UsuariosListaProyectoView.as_view(), name='usuarios-lista-proyecto-direct'),
    re_path(r'^usuarios/?$', auth_views.UsuariosListView.as_view(), name='usuarios-list-direct'),
    
    # Proyecto direct routes
    re_path(r'^proyecto/nuevo/?$', auth_views.ProyectoNuevoView.as_view(), name='proyecto-nuevo-direct'),
    re_path(r'^proyecto/lista/?$', auth_views.ProyectoListaView.as_view(), name='proyecto-lista-direct'),
    re_path(r'^proyecto/editar/?$', auth_views.ProyectoEditarView.as_view(), name='proyecto-editar-direct'),
    re_path(r'^proyecto/eliminar/?$', auth_views.ProyectoEliminarView.as_view(), name='proyecto-eliminar-direct'),
    
    # Vehiculo direct routes
    re_path(r'^vehiculo/nuevo/?$', auth_views.VehiculoNuevoView.as_view(), name='vehiculo-nuevo-direct'),
    
    # Tipo Usuario direct routes
    re_path(r'^tipo_usuarios/nuevo/?$', auth_views.TipoUsuarioNuevoView.as_view(), name='tipo-usuario-nuevo-direct'),
    re_path(r'^tipo_usuarios/lista/?$', auth_views.TipoUsuarioListaView.as_view(), name='tipo-usuario-lista-direct'),
    re_path(r'^tipo_usuarios/editar/?$', auth_views.TipoUsuarioEditarView.as_view(), name='tipo-usuario-editar-direct'),
    re_path(r'^tipo_usuarios/eliminar/?$', auth_views.TipoUsuarioEliminarView.as_view(), name='tipo-usuario-eliminar-direct'),
    
    # Tipo Documento direct routes
    re_path(r'^tipo_documento/nuevo/?$', auth_views.TipoDocumentoNuevoView.as_view(), name='tipo-documento-nuevo-direct'),
    re_path(r'^tipo_documento/lista_activos/?$', auth_views.TipoDocumentoListaActivosView.as_view(), name='tipo-documento-lista-activos-direct'),
    re_path(r'^tipo_documento/lista/?$', auth_views.TipoDocumentoListaView.as_view(), name='tipo-documento-lista-direct'),
    re_path(r'^tipo_documento/editar/?$', auth_views.TipoDocumentoEditarView.as_view(), name='tipo-documento-editar-direct'),
    re_path(r'^tipo_documento/eliminar/?$', auth_views.TipoDocumentoEliminarView.as_view(), name='tipo-documento-eliminar-direct'),
    
    path('api/pdf/', include('pdfconvert.urls')),
    path('api/ocr/', include('ocr.urls')),
]

