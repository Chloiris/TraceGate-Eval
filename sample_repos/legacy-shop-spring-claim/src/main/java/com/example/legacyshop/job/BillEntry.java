package com.example.legacyshop.job;

public class BillEntry {
    private final String id;
    private final String syncBatchId;
    private final long amountInCent;

    public BillEntry(String id, String syncBatchId, long amountInCent) {
        this.id = id;
        this.syncBatchId = syncBatchId;
        this.amountInCent = amountInCent;
    }

    public String getId() {
        return id;
    }

    public String getSyncBatchId() {
        return syncBatchId;
    }

    public long getAmountInCent() {
        return amountInCent;
    }
}
