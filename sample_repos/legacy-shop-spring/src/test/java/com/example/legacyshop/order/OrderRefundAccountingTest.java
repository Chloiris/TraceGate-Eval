package com.example.legacyshop.order;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class OrderRefundAccountingTest {
    @Autowired
    private OrderService orderService;

    @Test
    void refundAccountingUsesRefundStatusNotOrderStatus() {
        ShopOrder order = orderService.createPaidOrder("O-200");

        assertThat(orderService.requiresRefundAccounting(order)).isFalse();

        orderService.markRefundSuccess(order);

        assertThat(order.getOrderStatus()).isEqualTo(OrderStatus.PAID);
        assertThat(orderService.requiresRefundAccounting(order)).isTrue();
    }
}
