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
            request.user = User.objects.get(id=decoded.get('id'))
            return True
        except Exception:
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
        user = request.user
        payload = {
            'id': user.id,
            'email': user.email,
            'username': user.username,
        }
        return Response(payload)
