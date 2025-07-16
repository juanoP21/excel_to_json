import jwt
import bcrypt
import datetime
from django.conf import settings
from django.db import connection
from rest_framework.views import APIView
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from rest_framework import status


def get_usuario_by_email(email: str):
    """Return a user dict from the custom 'usuario' table."""
    keys = [
        'id_usuario',
        'useremail',
        'password',
        'nombre_usuario',
        'apellidos_usuario',
        'rol',
        'proyecto_id_proyecto',
    ]
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT id_usuario, useremail, password, nombre_usuario, '
            'apellidos_usuario, rol, proyecto_id_proyecto '
            'FROM usuario WHERE LOWER(useremail) = %s',
            [email],
        )
        row = cursor.fetchone()
    return dict(zip(keys, row)) if row else None


class JwtAuthGuard(BasePermission):
    """Simple JWT authentication guard."""

    def has_permission(self, request, view):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return False
        try:
            _, token = auth_header.split(' ')
        except ValueError:
            return False
        try:
            decoded = jwt.decode(
                token,
                settings.SECRETKEY,
                algorithms=['HS256'],
            )
            # Store the decoded JWT data directly as req.user (like Express)
            request.user = decoded
            return True
        except Exception as e:
            print(f"JWT Auth error: {e}")
            return False


class RegisterView(APIView):
    """Register new users."""

    def post(self, request, *args, **kwargs):
        data = request.data
        
        # Get all the fields from request body (like Express)
        password = data.get('password')
        nombre_usuario = data.get('nombre_usuario')
        apellidos_usuario = data.get('apellidos_usuario')
        googleid = data.get('googleid')
        useremail = data.get('useremail')
        userimg = data.get('userimg')
        username = data.get('username')
        telefono_usuario = data.get('telefono_usuario')
        documento_usuario = data.get('documento_usuario')
        tipo_usuario_id_tipo_usuario = data.get('tipo_usuario_id_tipo_usuario')
        proyecto_id_proyecto = data.get('proyecto_id_proyecto')
        estado_usuario = data.get('estado_usuario')
        rol = data.get('rol')
        disponibilidad = data.get('disponibilidad')
        
        if not password:
            return Response(
                {'error': 'Password is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            # Hash password like Express (bcrypt with salt rounds 10)
            hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            
            # Insert into usuario table with all fields
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO usuario (
                        password,
                        nombre_usuario,
                        apellidos_usuario,
                        googleid,
                        useremail,
                        userimg,
                        username,
                        telefono_usuario,
                        documento_usuario,
                        tipo_usuario_id_tipo_usuario,
                        proyecto_id_proyecto,
                        estado_usuario,
                        rol,
                        disponibilidad
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                    RETURNING id_usuario, useremail, nombre_usuario, apellidos_usuario, username, rol
                """, [
                    hashed_password,
                    nombre_usuario,
                    apellidos_usuario,
                    googleid,
                    useremail,
                    userimg,
                    username,
                    telefono_usuario,
                    documento_usuario,
                    tipo_usuario_id_tipo_usuario,
                    proyecto_id_proyecto,
                    estado_usuario,
                    rol,
                    disponibilidad
                ])
                
                # Get the returned row
                row = cursor.fetchone()
                if row:
                    keys = ['id_usuario', 'useremail', 'nombre_usuario', 'apellidos_usuario', 'username', 'rol']
                    new_user = dict(zip(keys, row))
                    return Response(new_user, status=status.HTTP_201_CREATED)
                else:
                    return Response(
                        {'error': 'Failed to create user'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                    
        except Exception as err:
            print(f"Register error: {err}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LoginView(APIView):
    """Authenticate user and return JWT following the Express logic."""

    def post(self, request, *args, **kwargs):
        # Accept both 'useremail' (to mirror the Express implementation) and
        # plain 'email' for backwards compatibility.
        useremail = request.data.get('useremail') or request.data.get('email')
        useremail = (useremail or '').lower()
        password = request.data.get('password')
        if not useremail or not password:
            return Response(
                {'error': 'Missing credentials'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = get_usuario_by_email(useremail)
        if not user:
            return Response(
                {'error': 'Correo electrónico incorrecto'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not bcrypt.checkpw(password.encode(), user['password'].encode()):
            return Response(
                {'error': 'Contraseña incorrecta'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user_payload = {
            key: user.get(key)
            for key in [
                'id_usuario',
                'useremail',
                'nombre_usuario',
                'apellidos_usuario',
                'rol',
                'proyecto_id_proyecto',
            ]
        }

        jwt_payload = {
            **user_payload,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1),
        }

        token = jwt.encode(jwt_payload, settings.SECRETKEY, algorithm='HS256')

        return Response({'serviceToken': token, 'user': user_payload})


class ProfileView(APIView):
    """Return user profile if authenticated."""

    permission_classes = [JwtAuthGuard]

    def get(self, request, *args, **kwargs):
        # Return the decoded JWT user data (like Express)
        return Response({'user': request.user})

class UsuarioDetailView(APIView):
    """Get user details by ID."""
    def get(self, request, id_usuario, *args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT id_usuario, useremail, nombre_usuario, apellidos_usuario, rol, proyecto_id_proyecto '
                'FROM usuario WHERE id_usuario = %s',
                [id_usuario]
            )
            row = cursor.fetchone()
        
        if not row:
            return Response(
                {'error': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        keys = ['id_usuario', 'useremail', 'nombre_usuario', 'apellidos_usuario', 'rol', 'proyecto_id_proyecto']
        user_data = dict(zip(keys, row))
        
        return Response(user_data)

class RoleAuthGuard(BasePermission):
    """Authorization guard for specific roles."""
    
    def has_permission(self, request, view):
        # First check JWT authentication
        jwt_guard = JwtAuthGuard()
        if not jwt_guard.has_permission(request, view):
            return False
            
        # Check if user has required role
        user_role = request.user.get('rol')
        allowed_roles = ['adminSistemas', 'usuario', 'aprobador_cargue']
        
        if user_role in allowed_roles:
            return True
        else:
            return False

class UsuariosListaProyectoView(APIView):
    """Get users list by project ID."""
    
    def get(self, request, proyecto, *args, **kwargs):
        try:
            # Convert proyecto to integer (like Express)
            proyecto = int(proyecto)
        except ValueError:
            return Response(
                {'error': 'Invalid project ID'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        usuario.id_usuario,
                        usuario.nombre_usuario,
                        usuario.apellidos_usuario,
                        usuario.googleid,
                        usuario.useremail,
                        usuario.userimg,
                        usuario.username,
                        usuario.telefono_usuario,
                        usuario.documento_usuario,
                        usuario.tipo_usuario_id_tipo_usuario,
                        usuario.proyecto_id_proyecto,
                        usuario.estado_usuario,
                        tipo_usuario.tipo_usuario,
                        tipo_usuario.id_tipo_usuario,
                        proyecto.nombre_proyecto,
                        proyecto.descripcion_proyecto
                    FROM 
                        usuario
                    INNER JOIN 
                        tipo_usuario ON usuario.tipo_usuario_id_tipo_usuario = tipo_usuario.id_tipo_usuario
                    INNER JOIN 
                        proyecto ON usuario.proyecto_id_proyecto = proyecto.id_proyecto
                    WHERE 
                        usuario.proyecto_id_proyecto = %s
                """, [proyecto])
                
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries (like Express rows)
                keys = [
                    'id_usuario', 'nombre_usuario', 'apellidos_usuario', 'googleid',
                    'useremail', 'userimg', 'username', 'telefono_usuario',
                    'documento_usuario', 'tipo_usuario_id_tipo_usuario', 'proyecto_id_proyecto',
                    'estado_usuario', 'tipo_usuario', 'id_tipo_usuario',
                    'nombre_proyecto', 'descripcion_proyecto'
                ]
                
                usuarios = [dict(zip(keys, row)) for row in rows]
                return Response(usuarios)
                
        except Exception as err:
            print(f"Error getting users by project: {err}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UsuariosListView(APIView):
    """Get all users with authentication and authorization."""
    
    permission_classes = [RoleAuthGuard]
    
    def get(self, request, *args, **kwargs):
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        usuario.id_usuario,
                        usuario.nombre_usuario,
                        usuario.apellidos_usuario,
                        usuario.googleid,
                        usuario.useremail,
                        usuario.userimg,
                        usuario.username,
                        usuario.telefono_usuario,
                        usuario.documento_usuario,
                        usuario.tipo_usuario_id_tipo_usuario,
                        usuario.proyecto_id_proyecto,
                        usuario.estado_usuario,
                        tipo_usuario.tipo_usuario,
                        tipo_usuario.id_tipo_usuario,
                        proyecto.nombre_proyecto,
                        proyecto.descripcion_proyecto
                    FROM usuario
                    INNER JOIN tipo_usuario ON usuario.tipo_usuario_id_tipo_usuario = tipo_usuario.id_tipo_usuario
                    INNER JOIN proyecto ON usuario.proyecto_id_proyecto = proyecto.id_proyecto
                """)
                
                rows = cursor.fetchall()
                
                # Convert to list of dictionaries (like Express rows)
                keys = [
                    'id_usuario', 'nombre_usuario', 'apellidos_usuario', 'googleid',
                    'useremail', 'userimg', 'username', 'telefono_usuario',
                    'documento_usuario', 'tipo_usuario_id_tipo_usuario', 'proyecto_id_proyecto',
                    'estado_usuario', 'tipo_usuario', 'id_tipo_usuario',
                    'nombre_proyecto', 'descripcion_proyecto'
                ]
                
                usuarios = [dict(zip(keys, row)) for row in rows]
                return Response(usuarios)
                
        except Exception as err:
            print(f"Error getting all users: {err}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ===========================================
# PROYECTO ENDPOINTS
# ===========================================

class ProyectoNuevoView(APIView):
    """Create new project."""
    
    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            nombre_proyecto = data.get('nombre_proyecto')
            descripcion_proyecto = data.get('descripcion_proyecto')
            estado_proyecto = data.get('estado_proyecto')
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO proyecto
                    (nombre_proyecto, descripcion_proyecto, estado_proyecto)
                    VALUES (%s, %s, %s) RETURNING *
                """, [nombre_proyecto, descripcion_proyecto, estado_proyecto])
                
                row = cursor.fetchone()
                if row:
                    keys = ['id_proyecto', 'nombre_proyecto', 'descripcion_proyecto', 'estado_proyecto']
                    proyecto = dict(zip(keys, row))
                    return Response(proyecto, status=status.HTTP_201_CREATED)
                    
        except Exception as err:
            print(f"Error creating project: {err}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProyectoListaView(APIView):
    """Get all projects."""
    
    def get(self, request, *args, **kwargs):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM proyecto")
                rows = cursor.fetchall()
                
                keys = ['id_proyecto', 'nombre_proyecto', 'descripcion_proyecto', 'estado_proyecto']
                proyectos = [dict(zip(keys, row)) for row in rows]
                return Response(proyectos)
                
        except Exception as err:
            print(f"Error getting projects: {err}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProyectoEditarView(APIView):
    """Edit project."""
    
    def put(self, request, *args, **kwargs):
        try:
            data = request.data
            id_proyecto = data.get('id_proyecto')
            nombre_proyecto = data.get('nombre_proyecto')
            descripcion_proyecto = data.get('descripcion_proyecto')
            estado_proyecto = data.get('estado_proyecto')
            
            if not id_proyecto:
                return Response(
                    {'error': 'provide a field (id_proyecto)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE proyecto
                    SET
                    nombre_proyecto = COALESCE(%s, nombre_proyecto),
                    descripcion_proyecto = COALESCE(%s, descripcion_proyecto),
                    estado_proyecto = COALESCE(%s, estado_proyecto)
                    WHERE id_proyecto = %s
                """, [nombre_proyecto, descripcion_proyecto, estado_proyecto, id_proyecto])
                
                return Response({'message': 'Project updated successfully'})
                
        except Exception as err:
            print(f"Error updating project: {err}")
            return Response(
                {'error': 'Some error has occured failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProyectoEliminarView(APIView):
    """Delete project."""
    
    def delete(self, request, *args, **kwargs):
        try:
            data = request.data
            id_proyecto = data.get('id_proyecto')
            
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM proyecto WHERE id_proyecto = %s", [id_proyecto])
                return Response("Proyecto eliminado")
                
        except Exception as err:
            print(f"Error deleting project: {err}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ===========================================
# VEHICULO ENDPOINTS
# ===========================================

class VehiculoNuevoView(APIView):
    """Create new vehicle."""
    
    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            descripcion = data.get('descripcion')
            placa_vehiculo = data.get('placa_vehiculo')
            capacidad_vehiculo = data.get('capacidad_vehiculo')
            disponibilidad_vehiculo = data.get('disponibilidad_vehiculo')
            soat_vehiculo = data.get('soat_vehiculo')
            tecno_vehiculo = data.get('tecno_vehiculo')
            impuesto_vehiculo = data.get('impuesto_vehiculo')
            proyecto_id_proyecto = data.get('proyecto_id_proyecto')
            modelo = data.get('modelo')
            ciudad_matricula = data.get('ciudad_matricula')
            tipo_transporte = data.get('tipo_transporte')
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO vehiculo (
                        descripcion,
                        placa_vehiculo,
                        capacidad_vehiculo,
                        disponibilidad_vehiculo,
                        soat_vehiculo,
                        tecno_vehiculo,
                        impuesto_vehiculo,
                        proyecto_id_proyecto,
                        modelo,
                        ciudad_matricula,
                        tipo_transporte
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *
                """, [
                    descripcion, placa_vehiculo, capacidad_vehiculo, disponibilidad_vehiculo,
                    soat_vehiculo, tecno_vehiculo, impuesto_vehiculo, proyecto_id_proyecto,
                    modelo, ciudad_matricula, tipo_transporte
                ])
                
                row = cursor.fetchone()
                if row:
                    keys = [
                        'id_vehiculo', 'descripcion', 'placa_vehiculo', 'capacidad_vehiculo',
                        'disponibilidad_vehiculo', 'soat_vehiculo', 'tecno_vehiculo',
                        'impuesto_vehiculo', 'proyecto_id_proyecto', 'modelo',
                        'ciudad_matricula', 'tipo_transporte'
                    ]
                    vehiculo = dict(zip(keys, row))
                    return Response(vehiculo, status=status.HTTP_201_CREATED)
                    
        except Exception as err:
            print(f"Error creating vehicle: {err}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ===========================================
# TIPO USUARIO ENDPOINTS
# ===========================================

class TipoUsuarioNuevoView(APIView):
    """Create new user type."""
    
    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            tipo_usuario = data.get('tipo_usuario')
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO tipo_usuario (tipo_usuario) VALUES (%s) RETURNING *
                """, [tipo_usuario])
                
                row = cursor.fetchone()
                if row:
                    keys = ['id_tipo_usuario', 'tipo_usuario']
                    tipo_user = dict(zip(keys, row))
                    return Response(tipo_user, status=status.HTTP_201_CREATED)
                    
        except Exception as err:
            print(f"Error creating user type: {err}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TipoUsuarioListaView(APIView):
    """Get all user types."""
    
    def get(self, request, *args, **kwargs):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM tipo_usuario")
                rows = cursor.fetchall()
                
                keys = ['id_tipo_usuario', 'tipo_usuario']
                tipos_usuario = [dict(zip(keys, row)) for row in rows]
                return Response(tipos_usuario)
                
        except Exception as err:
            print(f"Error getting user types: {err}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TipoUsuarioEditarView(APIView):
    """Edit user type."""
    
    def put(self, request, *args, **kwargs):
        try:
            data = request.data
            tipo_usuario = data.get('tipo_usuario')
            id_tipo_usuario = data.get('id_tipo_usuario')
            
            if not tipo_usuario:
                return Response(
                    {'error': 'provide a field (tipo_usuario)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE tipo_usuario
                    SET tipo_usuario = COALESCE(%s, tipo_usuario)
                    WHERE id_tipo_usuario = %s
                """, [tipo_usuario, id_tipo_usuario])
                
                return Response({'message': 'User type updated successfully'})
                
        except Exception as err:
            print(f"Error updating user type: {err}")
            return Response(
                {'error': 'Some error has occured failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TipoUsuarioEliminarView(APIView):
    """Delete user type."""
    
    def delete(self, request, *args, **kwargs):
        try:
            data = request.data
            id_tipo_usuario = data.get('id_tipo_usuario')
            
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM tipo_usuario WHERE id_tipo_usuario = %s", [id_tipo_usuario])
                return Response("Tipo de usuario eliminado")
                
        except Exception as err:
            print(f"Error deleting user type: {err}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ===========================================
# TIPO DOCUMENTO ENDPOINTS
# ===========================================

class TipoDocumentoNuevoView(APIView):
    """Create new document type."""
    
    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            nombre_documento = data.get('nombre_documento')
            tipo_documento = data.get('tipo_documento')
            estado_documento = data.get('estado_documento')
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO tipo_documento
                    (nombre_documento, tipo_documento, estado_documento)
                    VALUES (%s, %s, %s) RETURNING *
                """, [nombre_documento, tipo_documento, estado_documento])
                
                row = cursor.fetchone()
                if row:
                    keys = ['id_tipo_documento', 'nombre_documento', 'tipo_documento', 'estado_documento']
                    tipo_doc = dict(zip(keys, row))
                    return Response(tipo_doc, status=status.HTTP_201_CREATED)
                    
        except Exception as err:
            print(f"Error creating document type: {err}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TipoDocumentoListaActivosView(APIView):
    """Get active document types."""
    
    def get(self, request, *args, **kwargs):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM tipo_documento WHERE estado_documento = true")
                rows = cursor.fetchall()
                
                keys = ['id_tipo_documento', 'nombre_documento', 'tipo_documento', 'estado_documento']
                tipos_documento = [dict(zip(keys, row)) for row in rows]
                return Response(tipos_documento)
                
        except Exception as err:
            print(f"Error getting active document types: {err}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TipoDocumentoListaView(APIView):
    """Get all document types."""
    
    def get(self, request, *args, **kwargs):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM tipo_documento")
                rows = cursor.fetchall()
                
                keys = ['id_tipo_documento', 'nombre_documento', 'tipo_documento', 'estado_documento']
                tipos_documento = [dict(zip(keys, row)) for row in rows]
                return Response(tipos_documento)
                
        except Exception as err:
            print(f"Error getting document types: {err}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TipoDocumentoEditarView(APIView):
    """Edit document type."""
    
    def put(self, request, *args, **kwargs):
        try:
            data = request.data
            id_tipo_documento = data.get('id_tipo_documento')
            nombre_documento = data.get('nombre_documento')
            tipo_documento = data.get('tipo_documento')
            estado_documento = data.get('estado_documento')
            
            if not id_tipo_documento:
                return Response(
                    {'error': 'provide a field (id_tipo_documento)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE tipo_documento
                    SET
                    nombre_documento = COALESCE(%s, nombre_documento),
                    tipo_documento = COALESCE(%s, tipo_documento),
                    estado_documento = COALESCE(%s, estado_documento)
                    WHERE id_tipo_documento = %s
                """, [nombre_documento, tipo_documento, estado_documento, id_tipo_documento])
                
                return Response({'message': 'Document type updated successfully'})
                
        except Exception as err:
            print(f"Error updating document type: {err}")
            return Response(
                {'error': 'Some error has occured failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TipoDocumentoEliminarView(APIView):
    """Delete document type."""
    
    def delete(self, request, *args, **kwargs):
        try:
            data = request.data
            id_tipo_documento = data.get('id_tipo_documento')
            
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM tipo_documento WHERE id_tipo_documento = %s", [id_tipo_documento])
                return Response("Tipo de documento eliminado")
                
        except Exception as err:
            print(f"Error deleting document type: {err}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
