package com.example.legacyshop.job;

import java.util.Collection;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Repository;

@Repository
public class BillRepository {
    private final Map<String, BillEntry> entries = new ConcurrentHashMap<>();

    public boolean existsBySyncBatchId(String syncBatchId) {
        return entries.values().stream()
            .anyMatch(entry -> entry.getSyncBatchId().equals(syncBatchId));
    }

    public BillEntry save(BillEntry entry) {
        entries.put(entry.getId(), entry);
        return entry;
    }

    public long count() {
        return entries.size();
    }

    public Collection<BillEntry> findAll() {
        return entries.values();
    }

    public void clear() {
        entries.clear();
    }
}
