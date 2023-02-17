# Taller de creación de un login

Antes de comenzar con la creción de una api login, necesitamos hacer dos cosas para no tener conflictos.

Si hacen uso de `db.sqlite3`, deben eliminar el archivo. Si utilizan otra base de datos, todas las tablas de las mismas.

Eliminar `migrations` de la aplicación `users`.

Recordar que el repositorio usado es el [siguiente](https://github.com/silabuzinc/DRF).

## Recordando simpleJWT

Para hacer uso de simpleJWT necesitamos instalarlo dentro de nuestro proyecto.

```py
pip install djangorestframework-simplejwt
```

Ahora, si recordamos el uso de simpleJWT era para generar la autenticación de usuarios, pero en un inicio lo hicimos de forma simple y sin la creación de un API que otras aplicaciones puedan utilizar. Por lo que, en este taller vamos a realizar la creación completa de una API que permita la creación(signup) y el ingreso(login) de usuario retornando un token que puedan utilizar otras aplicaciones.

## Creación de modelos

Ya no haremos uso del modelo que hemos creado, vamos a necesitar uno nuevo ya que estos usuarios van a formar parte de la autenticación que ofrece DRF.

La clase a utilizar va a ser `BaseUserManager`, la cual nos va a permitir crear un modelo personalizado de superusuarios, para que podamos utilizarlo dentro de nuestra API. Más información [aquí](https://docs.djangoproject.com/en/4.1/topics/auth/customizing/).

Dentro de `users/models.py`, añadimos lo siguiente:

```py
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()

        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superusuario necesita que is_staff sea verdadero")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superusuario necesita que is_superuser sea verdadero")

        return self.create_user(email=email, password=password, **extra_fields)
```

-   `.normalize_email(email)` permite que el email ingresado esté descapitalizado para que mantenga el formato estándar que se tiene.
    
-   `**extra_fields` permite el ingreso de otros argumentos adicionales, en este caso el añadido será el nombre de usuario y el nombre real del usuario.
    

Dentro de nuestro modelo manejamos tanto la creación de un usuario normal como el de un superusuario, en el caso del superusuario se añaden validaciones adicionales que requiere el rol.

Realizamos la migración de nuestro modelo.

Primero, dentro de settings.py comentaremos la siguiente línea.

```py
INSTALLED_APPS = [
   ...
   #'django.contrib.admin',
   ...
]
```

Y en las rutas de nuestra carpeta principal(drfcrud), comentamos lo siguiente:

```py
urlpatterns = [
   ...
   #path('admin/', admin.site.urls) 
   ...
]
```

Luego de hacer esos pasos realizamos la migración.

```shell
python manage.py makemigrations users

python manage.py migrate
```

Luego de haber realizado la migración, descomentamos todo lo anterior.

## Creación de nuestro token JWT personalizado

Como necesitamos que se creen tokens en base a los usuarios que creamos, necesitamos tener una función que realice este trabajo. Dentro de nuestra app de users, creamos el archivo `tokens.py`, el cual contendrá lo siguiente:

```py
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


def create_jwt_pair_for_user(user: User):
    refresh = RefreshToken.for_user(user)

    tokens = {"access": str(refresh.access_token), "refresh": str(refresh)}

    return tokens
```

-   `get_user_model()` retorna el modelo que utiliza la autenticación de Django para los usuarios.
    
-   Con `RefreshToke` creamos el par de tokens para nuestro usuario.
    

## Creación de los serializadores

Para nuestro login, haremos uso de 2 serializadores. Recordar que los 2 irán en un mismo archivo por lo que las importaciones mostradas solo se deben colocar una sola vez.

-   SignUp

```py
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.validators import ValidationError
from .models import User


class SignUpSerializer(serializers.ModelSerializer):
    email = serializers.CharField(max_length=80)
    username = serializers.CharField(max_length=45)
    password = serializers.CharField(min_length=8, write_only=True)

    class Meta:
        model = User
        fields = ["email", "username", "password"]

    def validate(self, attrs):

        email_exists = User.objects.filter(email=attrs["email"]).exists()
        if email_exists:
            raise ValidationError("El email ya ha sido usado")
        return super().validate(attrs)

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = super().create(validated_data)
        user.set_password(password)
        user.save()
        Token.objects.create(user=user)

        return user
```

En este serializador, solo definimos la creación de nuestro usuario en conjunto de la validación correspondiente para que no se usen mismos emails.

```py
password = validated_data.pop("password")
user = super().create(validated_data)
user.set_password(password)
```

Este fragmento de código sirve para sacar la contraseña de nuestra información para luego setearla.

Luego de crear el usuario se hace otra creación pero en el modelo `authtoken` en base al usuario.

Ahora, creamos el serializador para obtener todos nuestro usuarios creados:

-   GetUser

```py
from rest_framework import serializers
from .models import User

class GetUserSerializer(serializers.ModelSerializer):
    email = serializers.CharField(max_length=80)
    username = serializers.CharField(max_length=45)
    password = serializers.CharField(min_length=8, write_only=True)

    class Meta:
        model = User
        fields = ["email", "username", "password"]    
```

Este serializador únicamente se usará para el retorno del listado de todos los usuarios.

## Creación de vistas

Ahora, para la creación de vistas añadiremos 3 de estas:

-   SignUp

```py
from django.contrib.auth import authenticate
from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import SignUpSerializer, GetUserSerializer
from .tokens import create_jwt_pair_for_user
from rest_framework import viewsets
from .models import User
# Create your views here.


class SignUpView(generics.GenericAPIView):
    serializer_class = SignUpSerializer

    def post(self, request: Request):
        data = request.data

        serializer = self.serializer_class(data=data)

        if serializer.is_valid():
            serializer.save()

            response = {"message": "El usuario se creó correctamente", "data": serializer.data}

            return Response(data=response, status=status.HTTP_201_CREATED)

        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

Esta vista va a permitir la creación de usuarios. Funciona como un post normal.

-   Login

```py
class LoginView(APIView):

    def post(self, request: Request):
        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(email=email, password=password)
        if user is not None:
            tokens = create_jwt_pair_for_user(user)

            response = {"message": "Logeado correctamente", "email": email ,"tokens": tokens}
            return Response(data=response, status=status.HTTP_200_OK)

        else:
            return Response(data={"message": "Correo inválido o contraseña incorrecta"})

    def get(self, request: Request):
        content = {"user": str(request.user), "auth": str(request.auth)}

        return Response(data=content, status=status.HTTP_200_OK)
```

Dentro de esta vista es que hacemos uso dela función que creamos en el archivo `tokens.py`, en la cual obtenemos nuestras credenciales en base al usuario creado.

Si la información recibida pertenece a algún usuario, retornaremos un mensaje indicando que los datos son correctos, los tokens y el email del usuario al que pertenecen. Esto para que puedan ser usados en otras vistas. Por ejemplo, si modificamos nuestro TODO para que almacene el email del usuario al que le pertenecen y este dispone de autenticación, con esta ruta podríamos a acceder o crear los TODO's que le pertenecen al usuario logeado.

El método GET, es utilizado para retornar si estamos logeados o si es un usuario anónimo. Esto sería utilizado para las sesiones que se pueden crear en el frontend al momento de acceder.

-   List Users

```py
class GetUsers(viewsets.ReadOnlyModelViewSet):
    serializer_class = GetUserSerializer
    queryset = User.objects.all()
```

Finalmente, creamos la vista que nos va a permitir listar a todos los usuarios que hemos creado.

## Registrando nuestro modelo

Ahora registraremos nuestro modelo creado en el admin de Django, dentro de `users/admin.py`, añadimos lo siguiente:

```py
from django.contrib import admin

from .models import User

# Register your models here.

admin.site.register(User)
```

Con este ya tendríamos registrado nuestro modelo dentro de la administración de Django.

## Creando las rutas

Para nuestras rutas, vamos a añadir tanto las vistas que hemos creado como las que ofrece simpleJWT.

```py
from rest_framework import routers
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from . import views

router = routers.DefaultRouter()
router.register('', views.GetUsers)

urlpatterns = [
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("jwt/create/", TokenObtainPairView.as_view(), name="jwt_create"),
    path("jwt/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("jwt/verify/", TokenVerifyView.as_view(), name="token_verify"),
]

urlpatterns += router.urls
```

Con esto, ya tenemos registradas nuestras rutas de la aplicación

## Modificando configuración

Ahora necesitamos realizar algunos cambios en la configuración de nuestra aplicación. Dentro de `settings.py` añadiremos las siguiente líneas.

```py
INSTALLED_APPS = [
    # ...
    'rest_framework_simplejwt',
    'rest_framework.authtoken',
    'users',
]
```

Añadimos simpleJWT, el authtoken que ofrece drf y nuestra aplicación en el caso de que no la tengamos añadida.

Al final del archivo, añadiremos lo siguiente:

```py
AUTH_USER_MODEL = 'users.User'
```

Con esta variable definimos el modelo en el que se va a basar la autenticación de nuestra API.

Si tenemos todo creado de forma correcta, recordando que tenemos al router principal de la siguiente forma:

```py
# importaciones

urlpatterns = [
    # ...

    path('users/', include('users.urls')),
]
```

Si accedemos a la ruta `http://127.0.0.1:8000/users/`, deberíamos obtener la siguiente respuesta.

![GET](https://photos.silabuz.com/uploads/big/394843c88057a1bb1865ee08ea6a137e.PNG)

En este caso los usuarios que aparecen son los que hemos registrado para nuestras pruebas, en su caso no debería retornarles nada o con un mensaje indicando que no existe contenido.

## Probando nuestras rutas

Si accedemos a `http://127.0.0.1:8000/users/signup/`, obtendremos la siguiente vista y podremos rellenar los datos que pide la API.

![POST](https://photos.silabuz.com/uploads/big/198999b056a57d956436b9ca353a62f0.PNG)

Cuando creamos el usuario.

![Creado](https://photos.silabuz.com/uploads/big/c54eb4498e3da3ac3e937fc9a8a475bd.PNG)

Ahora, ya tenemos un nuevo usuario registrado, ¿si queremos hacer login con él?

Accedemos a la ruta `http://127.0.0.1:8000/users/login/` y enviaremos el email y la contraseña del usuario creado.}

Para el usuario que creamos, la información a enviar sería la siguiente:

```json
{
    "email": "example2@mail.com",
    "password": 12345678
}
```

![Ingreso de usuario](https://photos.silabuz.com/uploads/big/1f5a6cd4d5a528bc2445d2d2c0e6921d.PNG)

Obtenemos la siguiente respuesta.

![Loeado](https://photos.silabuz.com/uploads/big/c1be6a40ae4e47a51e0e5baed513cab2.PNG)

Como vemos, nos retorna los tokens y el email del usuario al que le pertenece las credenciales.

## Tarea opcional

Implementar el uso de esta api con la aplicación de TODO's.

Recordar que ya estamos retornando el email del usuario logeado, por lo que se tendría que añadir un campo en el modelo TODO, que almacene la referencia a la tabla usuario o mediante el email que estamos retornando.

Ejemplo de un campo que puede ser añadido al modelo.

```py
author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="todos")
```

Con el campo añadido y el uso de las rutas, podemos hacer un login para luego obtener los TODO's que le corresponden al usuario.

Entonces en base a esa lógica, investigar e implementar la conexión entre TODO's y usuarios.

[Slide](https://docs.google.com/presentation/d/e/2PACX-1vTctyo-FEDSjkJWudpd5pNedvXJ-t9htRqAy1ZGMd0Jr_ANdpQLb4sjBhRboG66dQa7j5MMzYrcONHT/embed?start=false&loop=false&delayms=3000)