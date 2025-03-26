from rest_framework import viewsets, permissions
from .models import User,Role,Invoice
from .permissions import IsAdminUser, IsFinanceTeam
from rest_framework.response import Response
from .serializers import CustomUserSerializer,InvoiceSerializer
from rest_framework.decorators import action

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['assign_role']:
            return [permissions.IsAdminUser()]
        return super().get_permissions()
    
    @action(detail=True, methods=['post'])
    def update_role(self, request, pk = None):
        user = self.get_object()
        if request.user.role != Role.ADMIN:
            return Response({'error': 'Only Admins can Alter roles'}, status=403)
        
        role = request.data.get('role')
        if role not in [choice[0] for choice in Role.choices]:
            return Response({'error': 'Invalid role, Select Either AI Engineer, FinanceTeam or Admin'}, status=400)
        
        user.role = role
        user.save()
        return Response({'message': f'Role updated to {role}'}, status=200)


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['view', 'retrieve', 'create', 'update', 'partial_update', 'destroy']:
            return [IsFinanceTeam or IsAdminUser]
        return super().get_permissions()
    
    def perform_create(self, serializer):
        user_id = self.request.data.get('user')
        user = User.objects.get(id=user_id)
        serializer.save(user=user)
    
    @action(detail=True, methods=['post'])
    def payment_link(self, request, pk=None):
        invoice = self.get_object()
        domain_url = request.build_absolute_uri('/').rstrip('/')

        checkout_session = create_checkout(invoice, domain_url)

        if checkout_session:
            # Update the invoice with payment details
            invoice.payment_url = checkout_session.url
            invoice.stripe_payment_intent_id = checkout_session.payment_intent
            invoice.save()

            return Response({
                'payment_url': checkout_session.url
            })
        else:
            return Response({
                'error': 'Could not create payment session'
            }, status=400)
    
    @action(detail=True, methods=['get'])
    def verify_payment(self, request, pk=None):
        invoice = self.get_object()
        
        if not invoice.stripe_payment_intent_id:
            return Response({
                'status': 'No payment initiated'
            })
        
        payment_status = verify_payment_intent(invoice.stripe_payment_intent_id)
        
        # Update invoice status if payment is successful
        if payment_status == 'succeeded' and invoice.status == 'Pending':
            invoice.status = 'Paid'
            invoice.save()
        
        return Response({
            'status': payment_status,
            'invoice_status': invoice.status
        })
