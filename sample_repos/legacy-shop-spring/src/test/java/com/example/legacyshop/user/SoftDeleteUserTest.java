package com.example.legacyshop.user;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class SoftDeleteUserTest {
    @Autowired
    private UserRepository userRepository;

    @Autowired
    private UserService userService;

    @BeforeEach
    void reset() {
        userRepository.clear();
    }

    @Test
    void deleteUserMarksStatusInsteadOfRemovingRow() {
        userRepository.save(new UserAccount(10L, "Carol"));

        userService.deleteUser(10L);

        UserAccount user = userRepository.findById(10L).orElseThrow();
        assertThat(user.getStatus()).isEqualTo(UserAccount.STATUS_DELETED);
        assertThat(userRepository.count()).isEqualTo(1);
    }
}
