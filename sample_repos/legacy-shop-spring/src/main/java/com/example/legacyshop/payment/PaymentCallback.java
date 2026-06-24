package com.example.legacyshop.payment;

import java.math.BigDecimal;

public class PaymentCallback {
    private final String tradeNo;
    private final long amountInCent;
    private final BigDecimal amountInYuan;
    private final String signature;

    public PaymentCallback(String tradeNo, long amountInCent, BigDecimal amountInYuan, String signature) {
        this.tradeNo = tradeNo;
        this.amountInCent = amountInCent;
        this.amountInYuan = amountInYuan;
        this.signature = signature;
    }

    public String getTradeNo() {
        return tradeNo;
    }

    public long getAmountInCent() {
        return amountInCent;
    }

    public BigDecimal getAmountInYuan() {
        return amountInYuan;
    }

    public String getSignature() {
        return signature;
    }
}
