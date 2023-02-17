from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.request import Request

from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin

from .serializers import TodoSerializer
from .models import Todo

# class TodoViewSet(ModelViewSet):
#     queryset = Todo.objects.all()
#     serializer_class = TodoSerializer


class TodoListUser(ListModelMixin, GenericViewSet):
    queryset = Todo.objects.all()
    serializer_class = TodoSerializer
    
    def get_queryset(self):
        return Todo.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request: Request):
        allowed_fields = {'title', 'body'}
        received_fields = set(request.data.keys())
        if not received_fields.issubset(allowed_fields):
            return Response({
            'ok': False,
            'message': 'Only "title" and "body" fields are allowed'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        if isinstance(request.data, list):
            return Response({
                'ok': False,
                'message': 'Only one resource'
            }, status=status.HTTP_400_BAD_REQUEST)

        title = request.data.get('title')
        body = request.data.get('body')

        todo = Todo.objects.create(title=title, body=body, user=request.user)

        serializer = self.serializer_class(todo)

        return Response({
            'ok': True,
            'message': f'Todo created for {request.user}'
        }, status=status.HTTP_201_CREATED)