package com.vjeyam.oddsapi.api;

import java.net.URI;
import java.util.HashMap;
import java.util.List;
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
        Map<String, Object> payload = (body == null) ? Map.of() : body;

        return restClient.post()
                .uri(URI.create(pythonBaseUrl + "/jobs/odds-snapshot"))
                .contentType(MediaType.APPLICATION_JSON)
                .body(payload)
                .retrieve()
                .body(Object.class);
    }

    public record ResultsRefreshRequest(
            List<String> dates,
            String league,
            Double step
    ) {}

    @PostMapping("/api/etl/results-refresh")
    public Object resultsRefresh(@RequestBody(required = false) ResultsRefreshRequest req) {

        String league = (req != null && req.league() != null && !req.league().isBlank())
                ? req.league()
                : "nba";

        Double step = (req != null && req.step() != null)
                ? req.step()
                : 0.05;

        // Pull ESPN Results
        Map<String, Object> espnPayload = new HashMap<>();
        espnPayload.put("league", league);
        if (req != null && req.dates() != null && !req.dates().isEmpty()) {
            espnPayload.put("dates", req.dates());
        }

        Object espn = restClient.post()
                .uri(URI.create(pythonBaseUrl + "/jobs/espn-results-pull"))
                .contentType(MediaType.APPLICATION_JSON)
                .body(espnPayload)
                .retrieve()
                .body(Object.class);

        // Build game_id_map
        Object mapped = restClient.post()
                .uri(URI.create(pythonBaseUrl + "/jobs/build-game-id-map"))
                .contentType(MediaType.APPLICATION_JSON)
                .body(Map.of())
                .retrieve()
                .body(Object.class);

        // Build joined fact
        Object joined = restClient.post()
                .uri(URI.create(pythonBaseUrl + "/jobs/build-fact-game-results-best-market"))
                .contentType(MediaType.APPLICATION_JSON)
                .body(Map.of())
                .retrieve()
                .body(Object.class);

        // Build calibration
        Object calibration = restClient.post()
                .uri(URI.create(pythonBaseUrl + "/jobs/build-calibration-favorite"))
                .contentType(MediaType.APPLICATION_JSON)
                .body(Map.of("step", step))
                .retrieve()
                .body(Object.class);

        return Map.of(
                "espn_results_pull", espn,
                "game_id_map", mapped,
                "fact_game_results_best_market", joined,
                "calibration_favorite", calibration
        );
    }
}
