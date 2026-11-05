package com.instakill.analytics;

import java.util.List;

public record AnalyticsResponse(
        List<WeeklyStats> weeklyStats,
        List<TopPost> topPosts,
        Double likeToCommentRatio,
        List<MediaTypeStats> avgLikesByMediaType,
        Double topPercentile
) {
    public record WeeklyStats(String week, long posts, long likes, long comments) {}
    public record TopPost(String postId, String content, long engagement) {}
    public record MediaTypeStats(String mediaType, double avgLikes) {}
}
