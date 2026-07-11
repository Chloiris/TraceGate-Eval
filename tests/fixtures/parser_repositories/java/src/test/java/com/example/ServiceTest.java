package com.example;

import com.example.Service;

public class ServiceTest {
    public void verifiesService() {
        if (new Service().run(1) != 2) {
            throw new AssertionError();
        }
    }
}
