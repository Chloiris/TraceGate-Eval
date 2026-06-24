package com.example.legacyshop.user;

import java.util.Collection;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Repository;

@Repository
public class UserRepository {
    private final Map<Long, UserAccount> users = new ConcurrentHashMap<>();

    public UserAccount save(UserAccount user) {
        users.put(user.getId(), user);
        return user;
    }

    public Optional<UserAccount> findById(Long id) {
        return Optional.ofNullable(users.get(id));
    }

    public void deleteById(Long id) {
        users.remove(id);
    }

    public Collection<UserAccount> findAll() {
        return users.values();
    }

    public long count() {
        return users.size();
    }

    public void clear() {
        users.clear();
    }
}
