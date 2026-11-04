package com.instakill.api.rest;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/media")
public class MediaController {

    private final Path mediaDir;

    public MediaController(@Value("${media.base-path}") String mediaBasePath) throws IOException {
        this.mediaDir = Paths.get(mediaBasePath).toAbsolutePath().normalize();
        Files.createDirectories(this.mediaDir);
    }

    @PostMapping
    public ResponseEntity<Map<String, String>> upload(@RequestParam("file") MultipartFile file) throws IOException {
        String original = file.getOriginalFilename();
        String extension = (original != null && original.contains("."))
                ? original.substring(original.lastIndexOf('.'))
                : "";
        String filename = UUID.randomUUID() + extension;
        file.transferTo(mediaDir.resolve(filename));
        return ResponseEntity.status(HttpStatus.CREATED).body(Map.of("mediaUrl", "/media/" + filename));
    }
}
