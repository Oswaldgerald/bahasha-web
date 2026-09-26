from rest_framework import serializers
from django.contrib.auth import authenticate
from users.models import User


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        user = authenticate(
            username=username,
            password=password
        )

        if not user:
            raise serializers.ValidationError(
                "Invalid username or password"
            )

        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    church_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "full_name",
            "phone_number",
            "email",
            "role",
            "church",
            "church_name",
        ]

    def get_church_name(self, obj):
        if obj.church:
            return obj.church.church_name
        return None