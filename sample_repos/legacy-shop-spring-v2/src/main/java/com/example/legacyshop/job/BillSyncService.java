package com.example.legacyshop.job;

import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class BillSyncService {
    private final BillRepository billRepository;

    public BillSyncService(BillRepository billRepository) {
        this.billRepository = billRepository;
    }

    public void syncBill(String syncBatchId, long amountInCent) {
        if (billRepository.existsBySyncBatchId(syncBatchId)) {
            return;
        }
        billRepository.save(new BillEntry(UUID.randomUUID().toString(), syncBatchId, amountInCent));
    }
}
