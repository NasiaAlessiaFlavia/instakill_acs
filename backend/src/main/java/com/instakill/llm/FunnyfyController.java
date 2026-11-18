package com.instakill.llm;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class FunnyfyController {

    private final FunnyfyService funnyfyService;

    public FunnyfyController(FunnyfyService funnyfyService) {
        this.funnyfyService = funnyfyService;
    }

    @PostMapping("/funnyfy")
    public FunnyfyResponse funnyfy(@RequestBody FunnyfyRequest request) {
        String funnyText = funnyfyService.funnyfy(request.text());
        return new FunnyfyResponse(funnyText);
    }
}
