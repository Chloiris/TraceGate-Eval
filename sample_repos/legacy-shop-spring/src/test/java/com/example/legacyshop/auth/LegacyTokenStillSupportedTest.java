package com.example.legacyshop.auth;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class LegacyTokenStillSupportedTest {
    @Autowired
    private AuthService authService;

    @Test
    void legacyTokenUsesStableMobilePrefix() {
        LoginResponse response = authService.login("bob", "secret");

        assertThat(response.getLegacyToken()).isEqualTo("legacy-bob-mobile");
    }
}
