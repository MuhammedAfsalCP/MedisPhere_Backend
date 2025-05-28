from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializer import RedemptionRequestSerializer,TransactionSerializer
from .permissions import IsDoctor
from .models import Transactions
class RedemptionRequestAPIView(APIView):
    permission_classes =[IsDoctor]
    def post(self, request):
        data = request.data.copy()  
        data['doctor'] = str(request.user.id)
        serializer = RedemptionRequestSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Redemption request submitted successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request):
        transactions = Transactions.objects.filter(doctor=request.user.id).order_by('-date')
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)
