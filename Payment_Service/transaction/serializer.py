from rest_framework import serializers
from .models import Transactions, StatusChoices

class RedemptionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transactions
        fields = ['doctor', 'amount']

    def create(self, validated_data):
        validated_data['status'] = StatusChoices.PENDING  
        return super().create(validated_data)
class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transactions
        fields = '__all__'