package com.instakill.infrastructure.notification;

import com.instakill.post.domain.Post;

public interface NotificationService {
    void notifyPostCreated(Post post, String authorUsername);
}
