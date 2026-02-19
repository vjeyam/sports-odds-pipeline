package com.vjeyam.oddsapi.api;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;

@RestController
public class GamesController {

    private final JdbcTemplate jdbc;

    public GamesController(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping("/api/games")
    public List<Map<String, Object>> games(
            @RequestParam(required = false) String date
    ) {
        // date format: YYYY-MM-DD (defaults to today)
        String day = (date == null || date.isBlank())
                ? LocalDate.now().toString()
                : date;

        // commence_time is stored as TEXT ISO, so filter by first 10 chars (YYYY-MM-DD)
        String sql = """
            SELECT
              event_id,
              commence_time,
              home_team,
              away_team,
              best_home_price_american,
              best_home_bookmaker_key,
              best_away_price_american,
              best_away_bookmaker_key
            FROM fact_best_market_moneyline_odds
            WHERE LEFT(commence_time, 10) = ?
            ORDER BY commence_time ASC
        """;

        return jdbc.queryForList(sql, day);
    }
}
