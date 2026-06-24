package com.example.legacyshop.payment;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class AmountUnitCompatibilityTest {
    @Autowired
    private PaymentCallbackService paymentCallbackService;

    @Test
    void yuanAmountMustNotReplaceCentAmountInSignature() {
        String centSignature = paymentCallbackService.expectedSignature("T-200", 1200);
        PaymentCallback valid = new PaymentCallback("T-200", 1200, new BigDecimal("12.00"), centSignature);

        String yuanSignature = paymentCallbackService.expectedSignature("T-200", 12);
        PaymentCallback invalid = new PaymentCallback("T-200", 1200, new BigDecimal("12.00"), yuanSignature);

        assertThat(paymentCallbackService.verifySignature(valid)).isTrue();
        assertThat(paymentCallbackService.verifySignature(invalid)).isFalse();
    }
}
