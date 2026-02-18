package com.vjeyam.oddsapi.api;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class ResultsController {

    private final JdbcTemplate jdbc;

    public ResultsController(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping("/api/games/joined")
    public List<Map<String, Object>> joinedGames(@RequestParam(required = false) String date) {
        String day = (date == null || date.isBlank())
                ? LocalDate.now().toString()
                : date;

        String sql = """
            SELECT
              odds_event_id,
              espn_event_id,
              commence_time,
              home_team,
              away_team,
              best_home_price_american,
              best_away_price_american,
              home_score,
              away_score,
              winner,
              favorite_side,
              underdog_side
            FROM fact_game_results_best_market
            WHERE commence_time IS NOT NULL
              AND LEFT(commence_time, 10) = ?
            ORDER BY commence_time ASC
        """;

        return jdbc.queryForList(sql, day);
    }
}
