package com.example.legacyshop.user;

import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Repository;

@Repository
public class AuditLogRepository {
    private final Map<Long, AuditLog> logs = new ConcurrentHashMap<>();

    public AuditLog save(AuditLog auditLog) {
        logs.put(auditLog.getId(), auditLog);
        return auditLog;
    }

    public Optional<AuditLog> findById(Long id) {
        return Optional.ofNullable(logs.get(id));
    }

    public void clear() {
        logs.clear();
    }
}
