from rest_framework.serializers import ModelSerializer, ValidationError

from .models import Todo

class TodoSerializer(ModelSerializer):
    class Meta:
        model = Todo
        fields = '__all__'
        read_only_fields = ('created_at', 'done_at', 'updated_at', 'deleted_at', )

    def validate_status(self, value):
        if value < 0:
            raise ValidationError('Status cannot be negative')
        return value