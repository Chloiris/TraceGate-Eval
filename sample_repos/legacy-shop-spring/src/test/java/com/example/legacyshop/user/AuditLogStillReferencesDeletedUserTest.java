package com.example.legacyshop.user;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class AuditLogStillReferencesDeletedUserTest {
    @Autowired
    private UserRepository userRepository;

    @Autowired
    private AuditLogRepository auditLogRepository;

    @Autowired
    private AuditService auditService;

    @Autowired
    private UserService userService;

    @BeforeEach
    void reset() {
        userRepository.clear();
        auditLogRepository.clear();
    }

    @Test
    void auditLogCanStillDescribeSoftDeletedUser() {
        userRepository.save(new UserAccount(11L, "Dave"));
        AuditLog log = auditService.recordUserAction(11L, "LOGIN");

        userService.deleteUser(11L);

        assertThat(auditService.describeUserAction(log.getId()))
            .contains("Dave")
            .contains("status=2");
    }
}
