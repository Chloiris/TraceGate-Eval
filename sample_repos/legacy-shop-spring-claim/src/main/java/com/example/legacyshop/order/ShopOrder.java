package com.example.legacyshop.order;

public class ShopOrder {
    private final String id;
    private OrderStatus orderStatus;
    private RefundStatus refundStatus;

    public ShopOrder(String id, OrderStatus orderStatus, RefundStatus refundStatus) {
        this.id = id;
        this.orderStatus = orderStatus;
        this.refundStatus = refundStatus;
    }

    public String getId() {
        return id;
    }

    public OrderStatus getOrderStatus() {
        return orderStatus;
    }

    public void setOrderStatus(OrderStatus orderStatus) {
        this.orderStatus = orderStatus;
    }

    public RefundStatus getRefundStatus() {
        return refundStatus;
    }

    public void setRefundStatus(RefundStatus refundStatus) {
        this.refundStatus = refundStatus;
    }
}
