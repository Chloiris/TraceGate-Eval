package com.example.legacyshop.user;

public class AuditLog {
    private final Long id;
    private final Long userId;
    private final String action;

    public AuditLog(Long id, Long userId, String action) {
        this.id = id;
        this.userId = userId;
        this.action = action;
    }

    public Long getId() {
        return id;
    }

    public Long getUserId() {
        return userId;
    }

    public String getAction() {
        return action;
    }
}
