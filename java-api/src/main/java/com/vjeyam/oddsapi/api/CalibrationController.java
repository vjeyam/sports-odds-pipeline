package com.vjeyam.oddsapi.api;

import java.util.List;
import java.util.Map;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class CalibrationController {

    private final JdbcTemplate jdbc;

    public CalibrationController(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @GetMapping("/api/analytics/calibration")
    public List<Map<String, Object>> calibration() {
        String sql = """
            SELECT
              bucket_label,
              bucket_min,
              bucket_max,
              n_games,
              favorite_win_rate,
              avg_implied_prob,
              diff_actual_minus_implied
            FROM fact_calibration_favorite
            ORDER BY bucket_min ASC
        """;
        return jdbc.queryForList(sql);
    }
}
