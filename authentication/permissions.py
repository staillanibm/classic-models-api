"""
RBAC permission classes for classicmodels API viewsets.

Roles are represented as Django Groups: admin, read_only, product_manager,
customer, support. A user's effective role set is their group memberships;
`is_superuser` (including the API-key SystemUser) is always treated as admin.
"""

from __future__ import annotations

from rest_framework import permissions

from classicmodels.models import Customer, Order

SAFE_METHODS = permissions.SAFE_METHODS


def _in_group(user, name: str) -> bool:
    return user.is_authenticated and user.groups.filter(name=name).exists()


def is_admin(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_superuser or _in_group(user, "admin")))


def is_read_only_role(user) -> bool:
    return _in_group(user, "read_only")


def is_product_manager(user) -> bool:
    return _in_group(user, "product_manager")


def is_customer_role(user) -> bool:
    return _in_group(user, "customer")


def is_support(user) -> bool:
    return _in_group(user, "support")


def get_customer_number(user) -> int | None:
    profile = getattr(user, "customer_profile", None)
    return profile.customernumber if profile else None


class RolePermission(permissions.BasePermission):
    """
    Base for role-based viewset permissions. Admin always passes.
    Subclasses implement `check(user, method)` for the has_permission level,
    and may override `owns_object` for object-level ownership checks.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if is_admin(user):
            return True
        return self.check(user, request.method)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if is_admin(user):
            return True
        if not self.check(user, request.method):
            return False
        return self.owns_object(user, obj)

    def check(self, user, method: str) -> bool:  # pragma: no cover - abstract
        raise NotImplementedError

    def owns_object(self, user, obj) -> bool:
        return True


class CatalogPermission(RolePermission):
    """ProductLine/Product: RW for admin/product_manager, read-only otherwise."""

    def check(self, user, method):
        if method in SAFE_METHODS:
            return is_read_only_role(user) or is_product_manager(user) or is_customer_role(user) or is_support(user)
        return is_product_manager(user)


class ReferenceDataPermission(RolePermission):
    """Office/Employee: read-only for read_only/product_manager/support, no customer access."""

    def check(self, user, method):
        if method in SAFE_METHODS:
            return is_read_only_role(user) or is_product_manager(user) or is_support(user)
        return False


class CustomerResourcePermission(RolePermission):
    """
    Customer model itself: read-only for read_only/product_manager/support;
    customer role may only read/update their own record.
    """

    def check(self, user, method):
        if is_customer_role(user):
            return get_customer_number(user) is not None
        if method in SAFE_METHODS:
            return is_read_only_role(user) or is_product_manager(user) or is_support(user)
        return False

    def owns_object(self, user, obj: Customer) -> bool:
        if is_customer_role(user):
            return obj.customernumber == get_customer_number(user)
        return True


class OrderPermission(RolePermission):
    """
    Orders: read-only for read_only/product_manager; customer has full RW on
    their own orders; support may read anything and update only `status`.
    """

    def check(self, user, method):
        if is_customer_role(user):
            return get_customer_number(user) is not None
        if is_support(user):
            return True  # object-level check restricts writes to `status`
        if method in SAFE_METHODS:
            return is_read_only_role(user) or is_product_manager(user)
        return False

    def has_object_permission(self, request, view, obj: Order):
        user = request.user
        if is_admin(user):
            return True
        if is_customer_role(user):
            return obj.customernumber_id == get_customer_number(user)
        if is_support(user):
            if request.method in SAFE_METHODS:
                return True
            if request.method in ("PATCH", "PUT"):
                return set(request.data.keys()) <= {"status"}
            return False
        if request.method in SAFE_METHODS:
            return is_read_only_role(user) or is_product_manager(user)
        return False


class OrderScopedPermission(RolePermission):
    """
    Payment/Orderdetail: same shape as Orders but ownership is resolved via
    the parent Order/Customer relation (see owns_object overrides per view).
    """

    def check(self, user, method):
        if is_customer_role(user):
            return get_customer_number(user) is not None
        if is_support(user):
            return True
        if method in SAFE_METHODS:
            return is_read_only_role(user) or is_product_manager(user)
        return False


class PaymentPermission(OrderScopedPermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if is_admin(user):
            return True
        if is_customer_role(user):
            return obj.customernumber_id == get_customer_number(user)
        if is_support(user):
            return request.method in SAFE_METHODS
        if request.method in SAFE_METHODS:
            return is_read_only_role(user) or is_product_manager(user)
        return False


class OrderdetailPermission(OrderScopedPermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if is_admin(user):
            return True
        if is_customer_role(user):
            return obj.ordernumber.customernumber_id == get_customer_number(user)
        if is_support(user):
            return request.method in SAFE_METHODS
        if request.method in SAFE_METHODS:
            return is_read_only_role(user) or is_product_manager(user)
        return False
