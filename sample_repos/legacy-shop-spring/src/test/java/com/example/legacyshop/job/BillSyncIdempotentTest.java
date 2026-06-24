package com.example.legacyshop.job;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class BillSyncIdempotentTest {
    @Autowired
    private BillRepository billRepository;

    @Autowired
    private BillSyncService billSyncService;

    @BeforeEach
    void reset() {
        billRepository.clear();
    }

    @Test
    void sameSyncBatchIsAppliedOnce() {
        billSyncService.syncBill("BATCH-100", 5000);
        billSyncService.syncBill("BATCH-100", 5000);

        assertThat(billRepository.count()).isEqualTo(1);
    }
}
