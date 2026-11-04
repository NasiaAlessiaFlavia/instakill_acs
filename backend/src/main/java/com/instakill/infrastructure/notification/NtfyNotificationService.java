package com.instakill.infrastructure.notification;

import com.instakill.post.domain.Post;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
public class NtfyNotificationService implements NotificationService {

    private static final Logger log = LoggerFactory.getLogger(NtfyNotificationService.class);

    private final RestClient restClient;
    private final String ntfyTopic;

    public NtfyNotificationService(@Value("${instakill.notifications.ntfy-topic}") String ntfyTopic) {
        this.restClient = RestClient.create();
        this.ntfyTopic = ntfyTopic;
    }

    @Override
    @Async
    public void notifyPostCreated(Post post, String authorUsername) {
        String message = "New post by @" + authorUsername +
                " | ID: " + post.id() +
                " | " + post.createdAt();
        try {
            restClient.post()
                    .uri("https://ntfy.sh/" + ntfyTopic)
                    .header("Title", "New Instakill Post")
                    .body(message)
                    .retrieve()
                    .toBodilessEntity();
            log.debug("Notification sent for post {}", post.id());
        } catch (Exception e) {
            log.warn("Failed to send notification for post {}: {}", post.id(), e.getMessage());
        }
    }
}
