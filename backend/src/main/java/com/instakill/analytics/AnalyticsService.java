package com.instakill.analytics;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Service
@Transactional(readOnly = true)
public class AnalyticsService {

    @PersistenceContext
    private EntityManager em;

    public AnalyticsResponse getAnalytics(UUID userId) {
        String uid = userId.toString();
        return new AnalyticsResponse(
                fetchWeeklyStats(uid),
                fetchTopPosts(uid),
                fetchLikeToCommentRatio(uid),
                fetchAvgLikesByMediaType(uid),
                fetchTopPercentile(uid)
        );
    }

    @SuppressWarnings("unchecked")
    private List<AnalyticsResponse.WeeklyStats> fetchWeeklyStats(String userId) {
        List<Object[]> rows = em.createNativeQuery("""
                SELECT strftime('%Y-W%W', datetime(created_at/1000, 'unixepoch')) AS week,
                       COUNT(*)                        AS posts,
                       SUM(like_count)                 AS likes,
                       SUM(comment_count)              AS comments
                FROM posts
                WHERE author_id = :userId
                GROUP BY strftime('%Y-W%W', datetime(created_at/1000, 'unixepoch'))
                ORDER BY week DESC
                """)
                .setParameter("userId", userId)
                .getResultList();

        return rows.stream()
                .map(r -> new AnalyticsResponse.WeeklyStats(
                        (String) r[0],
                        ((Number) r[1]).longValue(),
                        r[2] == null ? 0L : ((Number) r[2]).longValue(),
                        r[3] == null ? 0L : ((Number) r[3]).longValue()
                ))
                .toList();
    }

    @SuppressWarnings("unchecked")
    private List<AnalyticsResponse.TopPost> fetchTopPosts(String userId) {
        List<Object[]> rows = em.createNativeQuery("""
                SELECT id,
                       content,
                       (like_count + comment_count) AS engagement
                FROM posts
                WHERE author_id = :userId
                ORDER BY engagement DESC
                LIMIT 5
                """)
                .setParameter("userId", userId)
                .getResultList();

        return rows.stream()
                .map(r -> new AnalyticsResponse.TopPost(
                        (String) r[0],
                        (String) r[1],
                        ((Number) r[2]).longValue()
                ))
                .toList();
    }

    private Double fetchLikeToCommentRatio(String userId) {
        Object result = em.createNativeQuery("""
                SELECT CAST(SUM(like_count) AS REAL) / NULLIF(SUM(comment_count), 0)
                FROM posts
                WHERE author_id = :userId
                """)
                .setParameter("userId", userId)
                .getSingleResult();
        return result == null ? null : ((Number) result).doubleValue();
    }

    @SuppressWarnings("unchecked")
    private List<AnalyticsResponse.MediaTypeStats> fetchAvgLikesByMediaType(String userId) {
        List<Object[]> rows = em.createNativeQuery("""
                SELECT media_type,
                       AVG(like_count) AS avg_likes
                FROM posts
                WHERE author_id = :userId
                  AND media_type IS NOT NULL
                GROUP BY media_type
                ORDER BY media_type
                """)
                .setParameter("userId", userId)
                .getResultList();

        return rows.stream()
                .map(r -> new AnalyticsResponse.MediaTypeStats(
                        (String) r[0],
                        ((Number) r[1]).doubleValue()
                ))
                .toList();
    }

    private Double fetchTopPercentile(String userId) {
        Object result = em.createNativeQuery("""
                WITH user_avg AS (
                    SELECT author_id,
                           AVG(like_count + comment_count) AS avg_eng
                    FROM posts
                    GROUP BY author_id
                ),
                my_avg AS (
                    SELECT AVG(like_count + comment_count) AS avg_eng
                    FROM posts
                    WHERE author_id = :userId
                )
                SELECT CASE
                    WHEN (SELECT avg_eng FROM my_avg) IS NULL THEN NULL
                    WHEN (SELECT COUNT(*) FROM user_avg) = 0  THEN NULL
                    ELSE ROUND(
                        (1.0 - CAST(
                            (SELECT COUNT(*) FROM user_avg
                             WHERE avg_eng < (SELECT avg_eng FROM my_avg))
                        AS REAL) / (SELECT COUNT(*) FROM user_avg)
                        ) * 100, 1
                    )
                END
                """)
                .setParameter("userId", userId)
                .getSingleResult();
        return result == null ? null : ((Number) result).doubleValue();
    }
}
