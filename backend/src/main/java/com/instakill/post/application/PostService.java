package com.instakill.post.application;

import com.instakill.common.clock.Clock;
import com.instakill.common.error.ForbiddenException;
import com.instakill.common.error.NotFoundException;
import com.instakill.common.id.IdGenerator;
import com.instakill.feed.application.FeedService;
import com.instakill.feed.domain.FeedSort;
import com.instakill.infrastructure.notification.NotificationService;
import com.instakill.post.domain.Post;
import com.instakill.post.domain.PostRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class PostService {

    private final PostRepository posts;
    private final IdGenerator idGenerator;
    private final Clock clock;
    private final FeedService feedService;
    private final NotificationService notificationService;

    public PostService(PostRepository posts, IdGenerator idGenerator, Clock clock,
                       FeedService feedService, NotificationService notificationService) {
        this.posts = posts;
        this.idGenerator = idGenerator;
        this.clock = clock;
        this.feedService = feedService;
        this.notificationService = notificationService;
    }

    @Transactional
    public Post createPost(UUID authorId, String authorUsername, String content, String imageUrl) {
        Instant now = clock.now();
        Post post = new Post(
                idGenerator.generate(),
                authorId,
                content,
                imageUrl,
                now,
                now,
                0L,
                0L
        );
        Post saved = posts.save(post);
        notificationService.notifyPostCreated(saved, authorUsername);
        return saved;
    }

    public Post getPost(UUID id) {
        return posts.findById(id).orElseThrow(() -> new NotFoundException("Post not found"));
    }

    @Transactional
    public void deleteOwnPost(UUID postId, UUID requesterId) {
        Post post = getPost(postId);
        if (!post.authorId().equals(requesterId)) {
            throw new ForbiddenException("Cannot delete another user's post");
        }
        posts.deleteById(postId);
    }

    public List<Post> listFeed(FeedSort sort, int page, int size) {
        return feedService.listFeed(sort, page, size);
    }
}
