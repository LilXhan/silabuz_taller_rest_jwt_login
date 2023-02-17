from rest_framework.routers import DefaultRouter
from django.urls import path
from . import api 

router = DefaultRouter()

router.register('todos', api.TodoListUser, basename='todos')

# urlpatterns = [
#     path('todos/', api.TodoListUser, name='todoUser')
# ]

urlpatterns = router.urls