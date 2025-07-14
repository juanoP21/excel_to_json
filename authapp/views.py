import jwt
import bcrypt
import datetime
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework import status


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
            decoded = jwt.decode(token, settings.SECRETKEY, algorithms=['HS256'])
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
            return Response({'error': 'Missing fields'}, status=status.HTTP_400_BAD_REQUEST)
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = User.objects.create(
            username=data['username'],
            email=data['email'].lower(),
            password=hashed,
        )
        return Response({'id': user.id, 'email': user.email, 'username': user.username}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Authenticate user and return JWT following the Express logic."""

    def post(self, request, *args, **kwargs):
        # Accept both 'useremail' (to mirror the Express implementation) and
        # plain 'email' for backwards compatibility.
        useremail = request.data.get('useremail') or request.data.get('email')
        useremail = (useremail or '').lower()
        password = request.data.get('password')
        if not useremail or not password:
            return Response({'error': 'Missing credentials'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email__iexact=useremail)
        except User.DoesNotExist:
            return Response({'error': 'Correo electrónico incorrecto'}, status=status.HTTP_401_UNAUTHORIZED)

        if not bcrypt.checkpw(password.encode(), user.password.encode()):
            return Response({'error': 'Contraseña incorrecta'}, status=status.HTTP_401_UNAUTHORIZED)

        user_payload = {
            'id_usuario': user.id,
            'useremail': user.email,
            'nombre_usuario': user.first_name,
            'apellidos_usuario': user.last_name,
            'rol': 'admin' if user.is_staff else 'user',
            'proyecto_id_proyecto': None,
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
