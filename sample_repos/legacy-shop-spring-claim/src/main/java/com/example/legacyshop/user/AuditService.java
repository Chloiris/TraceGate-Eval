package com.example.legacyshop.user;

import java.util.concurrent.atomic.AtomicLong;
import org.springframework.stereotype.Service;

@Service
public class AuditService {
    private final AuditLogRepository auditLogRepository;
    private final UserRepository userRepository;
    private final AtomicLong ids = new AtomicLong(1);

    public AuditService(AuditLogRepository auditLogRepository, UserRepository userRepository) {
        this.auditLogRepository = auditLogRepository;
        this.userRepository = userRepository;
    }

    public AuditLog recordUserAction(Long userId, String action) {
        return auditLogRepository.save(new AuditLog(ids.getAndIncrement(), userId, action));
    }

    public String describeUserAction(Long auditLogId) {
        AuditLog log = auditLogRepository.findById(auditLogId)
            .orElseThrow(() -> new IllegalArgumentException("audit log not found: " + auditLogId));
        UserAccount user = userRepository.findById(log.getUserId())
            .orElseThrow(() -> new IllegalStateException("audit user was physically deleted"));
        return user.getName() + ":" + log.getAction() + ":status=" + user.getStatus();
    }
}
