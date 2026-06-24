package com.example.legacyshop.order;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class RefundStatusIndependenceTest {
    @Autowired
    private OrderService orderService;

    @Test
    void requestingRefundDoesNotChangeOrderStatus() {
        ShopOrder order = orderService.createPaidOrder("O-100");

        orderService.requestRefund(order);

        assertThat(order.getOrderStatus()).isEqualTo(OrderStatus.PAID);
        assertThat(order.getRefundStatus()).isEqualTo(RefundStatus.REQUESTED);
    }
}
