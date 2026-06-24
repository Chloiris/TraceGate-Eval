package com.example.legacyshop.payment;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import org.springframework.stereotype.Service;

@Service
public class PaymentCallbackService {
    private static final String SECRET = "legacy-secret";

    public boolean verifySignature(PaymentCallback callback) {
        String expected = expectedSignature(callback.getTradeNo(), callback.getAmountInCent());
        return expected.equals(callback.getSignature());
    }

    public String expectedSignature(String tradeNo, long amountInCent) {
        return sha256(buildSignaturePayload(tradeNo, amountInCent));
    }

    private String buildSignaturePayload(String tradeNo, long amountInCent) {
        return tradeNo + ":" + amountInCent + ":" + SECRET;
    }

    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder();
            for (byte b : bytes) {
                builder.append(String.format("%02x", b));
            }
            return builder.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 unavailable", e);
        }
    }
}
