package com.example;

import com.example.Helper;

public class Service extends BaseService implements ValueSource {
    public int run(int value) {
        return Helper.increment(value);
    }

    public int value() {
        return run(1);
    }
}
