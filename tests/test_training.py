"""Regressionstests für Datenaufbereitung und probabilistische Trainingshilfen."""

import os
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd
import torch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from energy_forecasting.training import (  # noqa: E402
    add_time_features,
    compute_probabilistic_metrics,
    merge_weather_features,
    prepare_time_series_data,
    quantile_crossing_penalty,
    select_feature_columns,
    sort_quantile_predictions,
)


class TrainingUtilsTest(unittest.TestCase):
    """Prüfe methodische Invarianten der gemeinsamen Trainingspipeline."""

    def test_prepare_time_series_data_fits_scaler_on_training_split_only(self):
        index = pd.date_range("2026-04-01", periods=30, freq="h")
        pv_values = np.concatenate([np.linspace(0, 10, 22), np.full(8, 1000.0)])
        df = pd.DataFrame(
            {
                "Photovoltaik [MWh]": pv_values,
                "Wind Onshore [MWh]": np.linspace(20, 30, 30),
                "Erdgas [MWh]": np.linspace(40, 50, 30),
            },
            index=index,
        )
        df = add_time_features(df)

        feature_cols, target_col, _ = select_feature_columns(df)
        prepared = prepare_time_series_data(df, feature_cols, target_col, window_size=4)

        self.assertLess(prepared.scaler_target.data_max_[0], 1000.0)

    def test_probabilistic_metrics_include_interval_and_crossing_checks(self):
        y_true = np.array([[10.0], [20.0], [30.0]])
        preds = [
            np.array([[9.0], [18.0], [28.0]]),
            np.array([[10.0], [19.0], [29.0]]),
            np.array([[11.0], [22.0], [27.0]]),
        ]

        metrics, calibration = compute_probabilistic_metrics(y_true, preds, (0.1, 0.5, 0.9))

        self.assertIn("Mean_Interval_Width_MWh", metrics)
        self.assertIn("Winkler_Score_80_MWh", metrics)
        self.assertGreater(metrics["Quantile_Crossing_Rate_percent"], 0)
        self.assertEqual(list(calibration["quantile"]), [0.1, 0.5, 0.9])

    def test_quantile_crossing_penalty_and_sorting(self):
        crossed = torch.tensor([[0.7, 0.5, 0.9], [0.1, 0.8, 0.6]])

        self.assertGreater(quantile_crossing_penalty(crossed).item(), 0)

        sorted_preds = sort_quantile_predictions(crossed.numpy())
        self.assertTrue(np.all(np.diff(sorted_preds, axis=1) >= 0))

    def test_merge_weather_features_prefixes_and_interpolates_columns(self):
        index = pd.date_range("2026-04-01", periods=4, freq="h")
        df = pd.DataFrame({"Photovoltaik [MWh]": [0.0, 5.0, 10.0, 3.0]}, index=index)

        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as handle:
            handle.write("Timestamp;Globalstrahlung;Bewoelkung\n")
            handle.write("2026-04-01 00:00;0,0;80\n")
            handle.write("2026-04-01 02:00;400,0;30\n")
            weather_path = handle.name

        try:
            merged, weather_cols = merge_weather_features(df, weather_path)
        finally:
            os.remove(weather_path)

        self.assertEqual(weather_cols, ["weather_Globalstrahlung", "weather_Bewoelkung"])
        self.assertFalse(merged[weather_cols].isna().any().any())
        self.assertAlmostEqual(merged.loc[index[1], "weather_Globalstrahlung"], 200.0)


if __name__ == "__main__":
    unittest.main()
