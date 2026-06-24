package com.example.legacyshop.job;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class DuplicateBillShouldNotBeInsertedTest {
    @Autowired
    private BillRepository billRepository;

    @Autowired
    private BillSyncService billSyncService;

    @BeforeEach
    void reset() {
        billRepository.clear();
    }

    @Test
    void manualRerunDoesNotInsertDuplicateBill() {
        billSyncService.syncBill("BATCH-200", 7300);
        billSyncService.syncBill("BATCH-200", 7300);
        billSyncService.syncBill("BATCH-201", 7300);

        assertThat(billRepository.count()).isEqualTo(2);
    }
}
