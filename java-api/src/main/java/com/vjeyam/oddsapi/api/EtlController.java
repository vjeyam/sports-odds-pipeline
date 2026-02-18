package com.vjeyam.oddsapi.api;

import java.net.URI;
import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestClient;

@RestController
public class EtlController {

    private final RestClient restClient;
    private final String pythonBaseUrl;

    public EtlController(
            RestClient.Builder restClientBuilder,
            @Value("${python.base-url}") String pythonBaseUrl
    ) {
        this.restClient = restClientBuilder.build();
        this.pythonBaseUrl = pythonBaseUrl;
    }

    @PostMapping("/api/etl/odds-snapshot")
    public Object runOddsSnapshot(@RequestBody(required = false) Map<String, Object> body) {
        // Allow empty body; default sport/regions handled by Python API
        Map<String, Object> payload = (body == null) ? Map.of() : body;

        return restClient.post()
                .uri(URI.create(pythonBaseUrl + "/jobs/odds-snapshot"))
                .contentType(MediaType.APPLICATION_JSON)
                .body(payload)
                .retrieve()
                .body(Object.class);
    }
}
