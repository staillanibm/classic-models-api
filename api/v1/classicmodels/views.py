from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from config.throttles import ReadThrottle, WriteThrottle

from authentication.permissions import (
    CatalogPermission,
    CustomerResourcePermission,
    OrderdetailPermission,
    OrderPermission,
    PaymentPermission,
    ReferenceDataPermission,
    get_customer_number,
    is_customer_role,
)

from classicmodels.models import (
    Customer,
    Employee,
    Office,
    Order,
    Orderdetail,
    Payment,
    Product,
    ProductLine,
)

from .serializers import (
    CustomerSerializer,
    EmployeeSerializer,
    OfficeSerializer,
    OrderdetailSerializer,
    OrderSerializer,
    PaymentSerializer,
    ProductLineSerializer,
    ProductSerializer,
)


class BaseModelViewSet(viewsets.ModelViewSet):
    """Base viewset with appropriate throttling for read/write operations."""

    throttle_classes = [ReadThrottle, WriteThrottle]


@extend_schema_view(
    list=extend_schema(
        operation_id="list_product_lines",
        tags=["Product Lines"],
        summary="List all product lines",
        description="Retrieve a paginated list of all product line categories in the system.",
    ),
    create=extend_schema(
        operation_id="create_product_line",
        tags=["Product Lines"],
        summary="Create a new product line",
        description="Add a new product line category to the system.",
    ),
    retrieve=extend_schema(
        operation_id="get_product_line",
        tags=["Product Lines"],
        summary="Get a specific product line",
        description="Retrieve detailed information about a specific product line by its identifier.",
    ),
    update=extend_schema(
        operation_id="update_product_line",
        tags=["Product Lines"],
        summary="Update a product line",
        description="Update all fields of an existing product line.",
    ),
    partial_update=extend_schema(
        operation_id="patch_product_line",
        tags=["Product Lines"],
        summary="Partially update a product line",
        description="Update specific fields of an existing product line.",
    ),
    destroy=extend_schema(
        operation_id="delete_product_line",
        tags=["Product Lines"],
        summary="Delete a product line",
        description="Remove a product line from the system.",
    ),
)
class ProductLineViewSet(BaseModelViewSet):
    permission_classes = [CatalogPermission]
    queryset = ProductLine.objects.all()
    serializer_class = ProductLineSerializer
    lookup_field = "productline"
    lookup_url_kwarg = "productline"

    @extend_schema(
        operation_id="get_product_line_products",
        tags=["Product Lines"],
        summary="Get products by product line",
        description="Retrieve all products in a specific product line category. This endpoint allows browsing products by category.",
        parameters=[
            OpenApiParameter(
                name="productline",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="The product line identifier",
                required=True,
            ),
        ],
        responses={200: ProductSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=["get"],
        url_path="products",
        url_name="products",
    )
    def products(self, request, **kwargs):
        """
        Get all products in a specific product line.

        Returns a paginated list of all products belonging to this product line,
        including product details, pricing, and inventory information.
        """
        # Get the product line using the lookup_field
        try:
            product_line = self.get_object()
        except ProductLine.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Product line not found.")

        products = Product.objects.filter(productline=product_line).select_related(
            "productline"
        )

        # Apply pagination
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        operation_id="list_products",
        tags=["Products"],
        summary="List all products",
        description="Retrieve a paginated list of all products in the catalog with their details.",
    ),
    create=extend_schema(
        operation_id="create_product",
        tags=["Products"],
        summary="Create a new product",
        description="Add a new product to the catalog with all required information.",
    ),
    retrieve=extend_schema(
        operation_id="get_product",
        tags=["Products"],
        summary="Get a specific product",
        description="Retrieve detailed information about a specific product by its code.",
    ),
    update=extend_schema(
        operation_id="update_product",
        tags=["Products"],
        summary="Update a product",
        description="Update all fields of an existing product in the catalog.",
    ),
    partial_update=extend_schema(
        operation_id="patch_product",
        tags=["Products"],
        summary="Partially update a product",
        description="Update specific fields of an existing product.",
    ),
    destroy=extend_schema(
        operation_id="delete_product",
        tags=["Products"],
        summary="Delete a product",
        description="Remove a product from the catalog.",
    ),
)
class ProductViewSet(BaseModelViewSet):
    permission_classes = [CatalogPermission]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = "productcode"
    lookup_url_kwarg = "productcode"

    @extend_schema(
        operation_id="get_product_order_details",
        tags=["Products"],
        summary="Get product order history",
        description="Retrieve all order details (sales) for a specific product. This endpoint provides the complete sales history for the product.",
        parameters=[
            OpenApiParameter(
                name="productcode",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="The product code",
                required=True,
            ),
        ],
        responses={200: OrderdetailSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=["get"],
        url_path="order-details",
        url_name="order-details",
    )
    def order_details(self, request, **kwargs):
        """
        Get all order details for a specific product.

        Returns a paginated list of all order line items containing this product,
        including quantities ordered, prices, and order information.
        """
        # Get the product using the lookup_field
        try:
            product = self.get_object()
        except Product.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Product not found.")

        order_details = Orderdetail.objects.filter(productcode=product).select_related(
            "productcode", "ordernumber"
        )

        # Apply pagination
        page = self.paginate_queryset(order_details)
        if page is not None:
            serializer = OrderdetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = OrderdetailSerializer(order_details, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        operation_id="list_offices",
        tags=["Offices"],
        summary="List all offices",
        description="Retrieve a paginated list of all company office locations worldwide.",
    ),
    create=extend_schema(
        operation_id="create_office",
        tags=["Offices"],
        summary="Create a new office",
        description="Add a new office location to the company's network.",
    ),
    retrieve=extend_schema(
        operation_id="get_office",
        tags=["Offices"],
        summary="Get a specific office",
        description="Retrieve detailed information about a specific office by its code.",
    ),
    update=extend_schema(
        operation_id="update_office",
        tags=["Offices"],
        summary="Update an office",
        description="Update all fields of an existing office location.",
    ),
    partial_update=extend_schema(
        operation_id="patch_office",
        tags=["Offices"],
        summary="Partially update an office",
        description="Update specific fields of an existing office location.",
    ),
    destroy=extend_schema(
        operation_id="delete_office",
        tags=["Offices"],
        summary="Delete an office",
        description="Remove an office location from the company network.",
    ),
)
class OfficeViewSet(BaseModelViewSet):
    permission_classes = [ReferenceDataPermission]
    queryset = Office.objects.all()
    serializer_class = OfficeSerializer
    lookup_field = "officecode"
    lookup_url_kwarg = "officecode"

    @extend_schema(
        operation_id="get_office_employees",
        tags=["Offices"],
        summary="Get employees by office",
        description="Retrieve all employees working in a specific office. This endpoint supports office management and organizational charts.",
        parameters=[
            OpenApiParameter(
                name="officecode",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="The office code",
                required=True,
            ),
        ],
        responses={200: EmployeeSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=["get"],
        url_path="employees",
        url_name="employees",
    )
    def employees(self, request, **kwargs):
        """
        Get all employees in a specific office.

        Returns a paginated list of all employees working in this office,
        including employee details, job titles, and contact information.
        """
        # Get the office using the lookup_field
        try:
            office = self.get_object()
        except Office.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Office not found.")

        employees = Employee.objects.filter(officecode=office).select_related(
            "officecode", "reportsto"
        )

        # Apply pagination
        page = self.paginate_queryset(employees)
        if page is not None:
            serializer = EmployeeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = EmployeeSerializer(employees, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        operation_id="list_employees",
        tags=["Employees"],
        summary="List all employees",
        description="Retrieve a paginated list of all employees in the organization with their details.",
    ),
    create=extend_schema(
        operation_id="create_employee",
        tags=["Employees"],
        summary="Create a new employee",
        description="Add a new employee to the organization with their job details and office assignment.",
    ),
    retrieve=extend_schema(
        operation_id="get_employee",
        tags=["Employees"],
        summary="Get a specific employee",
        description="Retrieve detailed information about a specific employee by their employee number.",
    ),
    update=extend_schema(
        operation_id="update_employee",
        tags=["Employees"],
        summary="Update an employee",
        description="Update all fields of an existing employee record.",
    ),
    partial_update=extend_schema(
        operation_id="patch_employee",
        tags=["Employees"],
        summary="Partially update an employee",
        description="Update specific fields of an existing employee record.",
    ),
    destroy=extend_schema(
        operation_id="delete_employee",
        tags=["Employees"],
        summary="Delete an employee",
        description="Remove an employee from the organization.",
    ),
)
class EmployeeViewSet(BaseModelViewSet):
    permission_classes = [ReferenceDataPermission]
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    lookup_field = "employeenumber"
    lookup_url_kwarg = "employeenumber"

    @extend_schema(
        operation_id="get_employee_reports",
        tags=["Employees"],
        summary="Get employees by manager",
        description="Retrieve all employees reporting to a specific manager. This endpoint supports organizational hierarchy and team management.",
        parameters=[
            OpenApiParameter(
                name="employeenumber",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="The employee number of the manager",
                required=True,
            ),
        ],
        responses={200: EmployeeSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=["get"],
        url_path="reports",
        url_name="reports",
    )
    def reports(self, request, **kwargs):
        """
        Get all employees reporting to a specific manager.

        Returns a paginated list of all employees who report to this manager,
        including employee details, job titles, and contact information.
        """
        # Get the manager using the lookup_field
        try:
            manager = self.get_object()
        except Employee.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Employee not found.")

        reports = Employee.objects.filter(reportsto=manager).select_related(
            "officecode", "reportsto"
        )

        # Apply pagination
        page = self.paginate_queryset(reports)
        if page is not None:
            serializer = EmployeeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = EmployeeSerializer(reports, many=True)
        return Response(serializer.data)

    @extend_schema(
        operation_id="get_employee_customers",
        tags=["Employees"],
        summary="Get customers by sales rep",
        description="Retrieve all customers assigned to a specific sales representative. This endpoint supports sales rep performance tracking and customer management.",
        parameters=[
            OpenApiParameter(
                name="employeenumber",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="The employee number of the sales representative",
                required=True,
            ),
        ],
        responses={200: CustomerSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=["get"],
        url_path="customers",
        url_name="customers",
    )
    def customers(self, request, **kwargs):
        """
        Get all customers assigned to a specific sales representative.

        Returns a paginated list of all customers assigned to this sales rep,
        including customer details, contact information, and credit limits.
        """
        # Get the sales rep using the lookup_field
        try:
            sales_rep = self.get_object()
        except Employee.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Employee not found.")

        customers = Customer.objects.filter(
            salesrepemployeenumber=sales_rep
        ).select_related("salesrepemployeenumber")

        # Apply pagination
        page = self.paginate_queryset(customers)
        if page is not None:
            serializer = CustomerSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CustomerSerializer(customers, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        operation_id="list_customers",
        tags=["Customers"],
        summary="List all customers",
        description="Retrieve a paginated list of all customers with their contact and credit information.",
    ),
    create=extend_schema(
        operation_id="create_customer",
        tags=["Customers"],
        summary="Create a new customer",
        description="Add a new customer to the system with their contact details and credit limit.",
    ),
    retrieve=extend_schema(
        operation_id="get_customer",
        tags=["Customers"],
        summary="Get a specific customer",
        description="Retrieve detailed information about a specific customer by their customer number.",
    ),
    update=extend_schema(
        operation_id="update_customer",
        tags=["Customers"],
        summary="Update a customer",
        description="Update all fields of an existing customer record.",
    ),
    partial_update=extend_schema(
        operation_id="patch_customer",
        tags=["Customers"],
        summary="Partially update a customer",
        description="Update specific fields of an existing customer record.",
    ),
    destroy=extend_schema(
        operation_id="delete_customer",
        tags=["Customers"],
        summary="Delete a customer",
        description="Remove a customer from the system.",
    ),
)
class CustomerViewSet(BaseModelViewSet):
    permission_classes = [CustomerResourcePermission]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    lookup_field = "customernumber"
    lookup_url_kwarg = "customernumber"

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if is_customer_role(user):
            return queryset.filter(customernumber=get_customer_number(user))
        return queryset

    @extend_schema(
        operation_id="get_customer_orders",
        tags=["Customers"],
        summary="Get customer sales history",
        description="Retrieve all orders for a specific customer. This endpoint provides the complete sales history for the customer.",
        parameters=[
            OpenApiParameter(
                name="customernumber",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="The customer number",
                required=True,
            ),
        ],
        responses={200: OrderSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=["get"],
        url_path="orders",
        url_name="orders",
    )
    def orders(self, request, **kwargs):
        """
        Get all orders for a specific customer.

        Returns a paginated list of all orders placed by the customer,
        including order status, dates, and other order details.
        """
        # Get the customer using the lookup_field
        # This will work whether the URL uses 'pk' or 'customernumber'
        try:
            customer = self.get_object()
        except Customer.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Customer not found.")
        orders = Order.objects.filter(customernumber=customer).select_related(
            "customernumber"
        )

        # Apply pagination
        page = self.paginate_queryset(orders)
        if page is not None:
            serializer = OrderSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    @extend_schema(
        operation_id="get_customer_payments",
        tags=["Customers"],
        summary="Get customer payment history",
        description="Retrieve all payments made by a specific customer. This endpoint provides the complete payment history for the customer.",
        parameters=[
            OpenApiParameter(
                name="customernumber",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="The customer number",
                required=True,
            ),
        ],
        responses={200: PaymentSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=["get"],
        url_path="payments",
        url_name="payments",
    )
    def payments(self, request, **kwargs):
        """
        Get all payments for a specific customer.

        Returns a paginated list of all payments made by the customer,
        including payment dates, amounts, and check numbers.
        """
        # Get the customer using the lookup_field
        try:
            customer = self.get_object()
        except Customer.DoesNotExist:
            from rest_framework.exceptions import NotFound

            raise NotFound("Customer not found.")

        payments = Payment.objects.filter(customernumber=customer).select_related(
            "customernumber"
        )

        # Apply pagination
        page = self.paginate_queryset(payments)
        if page is not None:
            serializer = PaymentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        operation_id="list_orders",
        tags=["Orders"],
        summary="List all orders",
        description="Retrieve a paginated list of all customer orders with their status and details.",
    ),
    create=extend_schema(
        operation_id="create_order",
        tags=["Orders"],
        summary="Create a new order",
        description="Create a new customer order with order date, required date, and status information.",
    ),
    retrieve=extend_schema(
        operation_id="get_order",
        tags=["Orders"],
        summary="Get a specific order",
        description="Retrieve detailed information about a specific order by its order number.",
    ),
    update=extend_schema(
        operation_id="update_order",
        tags=["Orders"],
        summary="Update an order",
        description="Update all fields of an existing order record.",
    ),
    partial_update=extend_schema(
        operation_id="patch_order",
        tags=["Orders"],
        summary="Partially update an order",
        description="Update specific fields of an existing order record.",
    ),
    destroy=extend_schema(
        operation_id="delete_order",
        tags=["Orders"],
        summary="Delete an order",
        description="Remove an order from the system.",
    ),
)
class OrderViewSet(BaseModelViewSet):
    permission_classes = [OrderPermission]
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    lookup_field = "ordernumber"
    lookup_url_kwarg = "ordernumber"

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if is_customer_role(user):
            return queryset.filter(customernumber=get_customer_number(user))
        return queryset

    @extend_schema(
        operation_id="get_order_order_details",
        tags=["Orders"],
        summary="Get order details by order",
        description="Retrieve all line items for a specific order. This endpoint supports order fulfillment and invoice generation.",
        parameters=[
            OpenApiParameter(
                name="ordernumber",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="The order number",
                required=True,
            ),
        ],
        responses={200: OrderdetailSerializer(many=True)},
    )
    @action(
        detail=True,
        methods=["get"],
        url_path="order-details",
        url_name="order-details",
    )
    def order_details(self, request, **kwargs):
        """
        Get all order details for a specific order.
        
        Returns a paginated list of all line items in this order,
        including product codes, quantities, prices, and line numbers.
        """
        # Get the order using the lookup_field
        try:
            order = self.get_object()
        except Order.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Order not found.")
        
        order_details = Orderdetail.objects.filter(ordernumber=order).select_related(
            "ordernumber", "productcode"
        )
        
        # Apply pagination
        page = self.paginate_queryset(order_details)
        if page is not None:
            serializer = OrderdetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = OrderdetailSerializer(order_details, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        operation_id="list_payments",
        tags=["Payments"],
        summary="List all payments",
        description="Retrieve a paginated list of all customer payment records with amounts and dates.",
    ),
    create=extend_schema(
        operation_id="create_payment",
        tags=["Payments"],
        summary="Create a new payment",
        description="Record a new customer payment with check number, amount, and payment date.",
    ),
    retrieve=extend_schema(
        operation_id="get_payment",
        tags=["Payments"],
        summary="Get a specific payment",
        description="Retrieve detailed information about a specific payment by customer number and check number.",
        parameters=[
            OpenApiParameter(
                name="customerNumber",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="The customer number",
                required=True,
            ),
            OpenApiParameter(
                name="checkNumber",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="The check number",
                required=True,
            ),
        ],
    ),
    update=extend_schema(
        operation_id="update_payment",
        tags=["Payments"],
        summary="Update a payment",
        description="Update all fields of an existing payment record.",
        parameters=[
            OpenApiParameter(
                name="customerNumber",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="The customer number",
                required=True,
            ),
            OpenApiParameter(
                name="checkNumber",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="The check number",
                required=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        operation_id="patch_payment",
        tags=["Payments"],
        summary="Partially update a payment",
        description="Update specific fields of an existing payment record.",
        parameters=[
            OpenApiParameter(
                name="customerNumber",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="The customer number",
                required=True,
            ),
            OpenApiParameter(
                name="checkNumber",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="The check number",
                required=True,
            ),
        ],
    ),
    destroy=extend_schema(
        operation_id="delete_payment",
        tags=["Payments"],
        summary="Delete a payment",
        description="Remove a payment record from the system.",
        parameters=[
            OpenApiParameter(
                name="customerNumber",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="The customer number",
                required=True,
            ),
            OpenApiParameter(
                name="checkNumber",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="The check number",
                required=True,
            ),
        ],
    ),
)
class PaymentViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Payment.objects.select_related("customernumber")
    serializer_class = PaymentSerializer
    permission_classes = [PaymentPermission]
    throttle_classes = [ReadThrottle, WriteThrottle]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if is_customer_role(user):
            return queryset.filter(customernumber=get_customer_number(user))
        return queryset

    def get_object(self):
        """Get object using composite key (customerNumber, checkNumber)."""
        customer_number = self.kwargs.get("customerNumber")
        check_number = self.kwargs.get("checkNumber")
        obj = get_object_or_404(
            Payment, customernumber_id=customer_number, checknumber=check_number
        )
        self.check_object_permissions(self.request, obj)
        return obj

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        operation_id="list_order_details",
        tags=["Order Details"],
        summary="List all order details",
        description="Retrieve a paginated list of all order line items with product and quantity information.",
    ),
    create=extend_schema(
        operation_id="create_order_detail",
        tags=["Order Details"],
        summary="Create a new order detail",
        description="Add a new line item to an existing order with product code, quantity, and price.",
    ),
    retrieve=extend_schema(
        operation_id="get_order_detail",
        tags=["Order Details"],
        summary="Get a specific order detail",
        description="Retrieve a specific line item from an order using the composite key (orderNumber, productCode).",
        parameters=[
            OpenApiParameter(
                name="orderNumber",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="The order number",
                required=True,
            ),
            OpenApiParameter(
                name="productCode",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="The product code",
                required=True,
            ),
        ],
    ),
    update=extend_schema(
        operation_id="update_order_detail",
        tags=["Order Details"],
        summary="Update an order detail",
        description="Update all fields of an existing order line item.",
        parameters=[
            OpenApiParameter(
                name="orderNumber",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="The order number",
                required=True,
            ),
            OpenApiParameter(
                name="productCode",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="The product code",
                required=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        operation_id="patch_order_detail",
        tags=["Order Details"],
        summary="Partially update an order detail",
        description="Update specific fields of an existing order line item.",
        parameters=[
            OpenApiParameter(
                name="orderNumber",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="The order number",
                required=True,
            ),
            OpenApiParameter(
                name="productCode",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="The product code",
                required=True,
            ),
        ],
    ),
    destroy=extend_schema(
        operation_id="delete_order_detail",
        tags=["Order Details"],
        summary="Delete an order detail",
        description="Remove a line item from an order.",
        parameters=[
            OpenApiParameter(
                name="orderNumber",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="The order number",
                required=True,
            ),
            OpenApiParameter(
                name="productCode",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description="The product code",
                required=True,
            ),
        ],
    ),
)
class OrderdetailViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Orderdetail.objects.select_related("ordernumber", "productcode")
    serializer_class = OrderdetailSerializer
    permission_classes = [OrderdetailPermission]
    throttle_classes = [ReadThrottle, WriteThrottle]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if is_customer_role(user):
            return queryset.filter(ordernumber__customernumber=get_customer_number(user))
        return queryset

    def get_object(self):
        """Get object using composite key (orderNumber, productCode)."""
        order_number = self.kwargs.get("orderNumber")
        product_code = self.kwargs.get("productCode")
        obj = get_object_or_404(
            Orderdetail, ordernumber_id=order_number, productcode_id=product_code
        )
        self.check_object_permissions(self.request, obj)
        return obj
