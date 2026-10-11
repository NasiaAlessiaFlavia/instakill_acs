package com.instakill.feed.application;

import com.instakill.post.domain.Post;
import com.instakill.post.domain.PostRepository;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class NewestFeedRankingStrategyTest {

    private final PostRepository repository = mock(PostRepository.class);
    private final NewestFeedRankingStrategy strategy = new NewestFeedRankingStrategy();

    @Test
    void delegatesToFindLatest() {
        List<Post> posts = List.of(
                post(Instant.now().minusSeconds(10)),
                post(Instant.now().minusSeconds(20))
        );
        when(repository.findLatest(0, 2)).thenReturn(posts);

        List<Post> result = strategy.fetch(repository, 0, 2);

        assertThat(result).isEqualTo(posts);
    }

    private Post post(Instant createdAt) {
        return new Post(UUID.randomUUID(), UUID.randomUUID(), "content", null, createdAt, createdAt, 0, 0);
    }
}
