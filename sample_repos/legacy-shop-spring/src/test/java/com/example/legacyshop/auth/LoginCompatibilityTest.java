package com.example.legacyshop.auth;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class LoginCompatibilityTest {
    @Autowired
    private AuthService authService;

    @Test
    void oldMobileClientStillReceivesLegacyToken() {
        LoginResponse response = authService.login("alice", "secret");

        assertThat(response.getAccessToken()).startsWith("access-alice");
        assertThat(response.getLegacyToken()).startsWith("legacy-alice");
    }
}
