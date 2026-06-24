package com.example.legacyshop.payment;

import static org.assertj.core.api.Assertions.assertThat;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class PaymentSignatureTest {
    @Autowired
    private PaymentCallbackService paymentCallbackService;

    @Test
    void signatureUsesOriginalCentAmount() {
        String signature = paymentCallbackService.expectedSignature("T-100", 1299);
        PaymentCallback callback = new PaymentCallback("T-100", 1299, new BigDecimal("12.99"), signature);

        assertThat(paymentCallbackService.verifySignature(callback)).isTrue();
    }
}
