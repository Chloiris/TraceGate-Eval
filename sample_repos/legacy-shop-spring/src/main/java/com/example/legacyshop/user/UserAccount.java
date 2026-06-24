package com.example.legacyshop.user;

public class UserAccount {
    public static final int STATUS_ACTIVE = 1;
    public static final int STATUS_DELETED = 2;

    private final Long id;
    private final String name;
    private int status;

    public UserAccount(Long id, String name) {
        this.id = id;
        this.name = name;
        this.status = STATUS_ACTIVE;
    }

    public Long getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public int getStatus() {
        return status;
    }

    public void markDeleted() {
        this.status = STATUS_DELETED;
    }
}
