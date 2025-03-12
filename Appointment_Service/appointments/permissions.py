from rest_framework.permissions import BasePermission

class IsDoctor(BasePermission):
    """Allow access only to doctors"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_doctor

class IsAdmin(BasePermission):
    """Allow access only to admins"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin

class IsStaff(BasePermission):
    """Allow access only to staff members"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff
