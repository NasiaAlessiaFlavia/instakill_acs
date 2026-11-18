package com.instakill.llm;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;

@Service
public class FunnyfyService {

    private final RestClient restClient;

    public FunnyfyService(@Value("${instakill.llm.url}") String llmUrl) {
        var factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(5_000);
        factory.setReadTimeout(30_000);
        this.restClient = RestClient.builder()
                .baseUrl(llmUrl)
                .requestFactory(factory)
                .build();
    }

    public String funnyfy(String text) {
        try {
            var body = Map.of(
                "model", "google/gemma-3-270m",
                "messages", List.of(
                    Map.of("role", "system",
                           "content", "Always reply with the user's message, but rewritten in a more funny style."),
                    Map.of("role", "user", "content", text)
                ),
                "max_tokens", 256,
                "temperature", 0.7,
                "stream", false
            );

            LlmResponse response = restClient.post()
                    .uri("/v1/chat/completions")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(body)
                    .retrieve()
                    .body(LlmResponse.class);

            return response.choices().get(0).message().content().strip();
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,
                    "LLM service unavailable – is LM Studio running on the configured port?");
        }
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record LlmResponse(List<Choice> choices) {
        @JsonIgnoreProperties(ignoreUnknown = true)
        record Choice(Message message) {}

        @JsonIgnoreProperties(ignoreUnknown = true)
        record Message(String content) {}
    }
}
