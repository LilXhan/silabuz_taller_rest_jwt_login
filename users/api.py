from django.contrib.auth import authenticate

from rest_framework import generics, status 
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAdminUser

from .serializers import GetUserSerializer, SingUpSerializer
from .tokens import create_jwt_pair_for_user
from .models import User


class SignUpView(generics.GenericAPIView):
    serializer_class = SingUpSerializer
    permission_classes = [AllowAny]
    def post(self, request: Request):
        data = request.data 

        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            serializer.save()

            response = {'ok': True, 'message': 'User created'}

            return Response(data=response, status=status.HTTP_201_CREATED)

        return Response({
            'ok': False,
            'message': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):

    permission_classes = [AllowAny]

    def post(self, request: Request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(email=email, password=password)

        if user is not None:
            tokens = create_jwt_pair_for_user(user)

            response = {'ok': True, 'message': 'Login success', 'email': email, 'tokens': tokens}

            return Response(data=response, status=status.HTTP_200_OK)

        else:
            return Response({
                    'ok': False,
                    'message': 'Invalid password or email'
                }, status=status.HTTP_200_OK
            )
    
    def get(self, request: Request):
        content = {'user': str(request.user), 'auth': str(request.auth)}

        return Response(data=content, status=status.HTTP_200_OK)

class GetUser(generics.mixins.ListModelMixin, viewsets.GenericViewSet, generics.mixins.RetrieveModelMixin):
    queryset = User.objects.all()
    serializer_class = GetUserSerializer
    permission_classes = [IsAdminUser]