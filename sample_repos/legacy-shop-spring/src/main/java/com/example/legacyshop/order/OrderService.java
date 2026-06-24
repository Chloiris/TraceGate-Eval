package com.example.legacyshop.order;

import org.springframework.stereotype.Service;

@Service
public class OrderService {
    public ShopOrder createPaidOrder(String id) {
        return new ShopOrder(id, OrderStatus.PAID, RefundStatus.NONE);
    }

    public void requestRefund(ShopOrder order) {
        order.setRefundStatus(RefundStatus.REQUESTED);
    }

    public void markRefundSuccess(ShopOrder order) {
        order.setRefundStatus(RefundStatus.SUCCESS);
    }

    public boolean requiresRefundAccounting(ShopOrder order) {
        return order.getRefundStatus() == RefundStatus.REQUESTED
            || order.getRefundStatus() == RefundStatus.SUCCESS;
    }

    public String displayStatus(ShopOrder order) {
        if (order.getRefundStatus() == RefundStatus.NONE) {
            return order.getOrderStatus().name();
        }
        return order.getOrderStatus().name() + "/" + order.getRefundStatus().name();
    }
}
