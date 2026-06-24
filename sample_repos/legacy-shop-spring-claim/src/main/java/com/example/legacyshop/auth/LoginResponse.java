package com.example.legacyshop.auth;

public class LoginResponse {
    private final String accessToken;
    private final String legacyToken;

    public LoginResponse(String accessToken, String legacyToken) {
        this.accessToken = accessToken;
        this.legacyToken = legacyToken;
    }

    public String getAccessToken() {
        return accessToken;
    }

    public String getLegacyToken() {
        return legacyToken;
    }
}
