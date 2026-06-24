package com.example.legacyshop.auth;

import org.springframework.stereotype.Service;

@Service
public class AuthService {
    public LoginResponse login(String username, String password) {
        validatePassword(password);
        String accessToken = generateAccessToken(username);
        String legacyToken = generateLegacyToken(username);
        return new LoginResponse(accessToken, legacyToken);
    }

    private void validatePassword(String password) {
        if (password == null || password.isBlank()) {
            throw new IllegalArgumentException("password is required");
        }
    }

    private String generateAccessToken(String username) {
        return "access-" + username + "-v2";
    }

    private String generateLegacyToken(String username) {
        return "legacy-" + username + "-mobile";
    }
}
