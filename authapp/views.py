import jwt
import bcrypt
import datetime
from django.conf import settings
from django.db import connection
from django.contrib.auth.models import User
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
        password = data.get('password')
        if not password or not data.get('username') or not data.get('email'):
            return Response(
                {'error': 'Missing fields'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = User.objects.create(
            username=data['username'],
            email=data['email'].lower(),
            password=hashed,
        )
        return Response(
            {
                'id': user.id,
                'email': user.email,
                'username': user.username,
            },
            status=status.HTTP_201_CREATED,
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
