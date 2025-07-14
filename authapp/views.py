import jwt
import bcrypt
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
    """Authenticate user and return JWT."""

    def post(self, request, *args, **kwargs):
        email = request.data.get('email', '').lower()
        password = request.data.get('password')
        if not email or not password:
            return Response({'error': 'Missing credentials'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Correo electrónico incorrecto'}, status=status.HTTP_401_UNAUTHORIZED)
        if not bcrypt.checkpw(password.encode(), user.password.encode()):
            return Response({'error': 'Contraseña incorrecta'}, status=status.HTTP_401_UNAUTHORIZED)
        payload = {
            'id': user.id,
            'email': user.email,
            'username': user.username,
        }
        token = jwt.encode(payload, settings.SECRETKEY, algorithm='HS256')
        return Response({'serviceToken': token, 'user': payload})


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
