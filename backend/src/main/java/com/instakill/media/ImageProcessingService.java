package com.instakill.media;

import net.coobird.thumbnailator.Thumbnails;
import org.springframework.stereotype.Service;

import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.Set;

@Service
public class ImageProcessingService {

    private static final int MAX_WIDTH = 300;
    private static final String WATERMARK_TEXT = "Instakill Demo";
    private static final Set<String> IMAGE_EXTENSIONS = Set.of(".jpg", ".jpeg", ".png", ".gif", ".webp");

    public boolean isImage(String extension) {
        return IMAGE_EXTENSIONS.contains(extension.toLowerCase());
    }

    public byte[] process(InputStream inputStream, String extension) throws IOException {
        String format = resolveFormat(extension);
        BufferedImage original = ImageIO.read(inputStream);
        if (original == null) {
            throw new IOException("Could not decode image");
        }

        BufferedImage resized = original.getWidth() > MAX_WIDTH
                ? Thumbnails.of(original).width(MAX_WIDTH).asBufferedImage()
                : original;

        addWatermark(resized);

        ByteArrayOutputStream out = new ByteArrayOutputStream();
        ImageIO.write(resized, format, out);
        return out.toByteArray();
    }

    private void addWatermark(BufferedImage image) {
        Graphics2D g = image.createGraphics();
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setFont(new Font("Arial", Font.BOLD, 12));
        FontMetrics fm = g.getFontMetrics();
        int x = image.getWidth() - fm.stringWidth(WATERMARK_TEXT) - 8;
        int y = image.getHeight() - 8;
        g.setColor(new Color(0, 0, 0, 100));
        g.drawString(WATERMARK_TEXT, x + 1, y + 1);
        g.setColor(new Color(255, 255, 255, 180));
        g.drawString(WATERMARK_TEXT, x, y);
        g.dispose();
    }

    private String resolveFormat(String extension) {
        return switch (extension.toLowerCase()) {
            case ".jpg", ".jpeg" -> "jpeg";
            case ".gif" -> "gif";
            case ".webp" -> "webp";
            default -> "png";
        };
    }
}
