"""LSTM-Architektur und ausführbarer Einstiegspunkt der Trainingspipeline."""

import torch.nn as nn

from energy_forecasting.training import run_probabilistic_training


class ProbabilisticLSTM(nn.Module):
    """LSTM, das die drei konfigurierten Quantile gemeinsam ausgibt."""

    def __init__(self, input_size, hidden_size=128, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        self.linear = nn.Linear(hidden_size, 3)

    def forward(self, x):
        """Bilde Sequenzen der Form ``(Batch, Zeit, Features)`` auf drei Quantile ab."""

        out, _ = self.lstm(x)
        return self.linear(out[:, -1, :])


def build_model(input_size):
    """Erzeuge die von der gemeinsamen Trainingspipeline erwartete Architektur."""

    return ProbabilisticLSTM(input_size=input_size)


if __name__ == "__main__":
    run_probabilistic_training(
        model_factory=build_model,
        architecture="LSTM",
        output_prefix="lstm",
        color="blue",
        checkpoint_path="best_prob_model.pth",
        final_model_path="final_probabilistic_lstm.pth",
        scaler_features_path="scaler_features.pkl",
        scaler_target_path="scaler_target.pkl",
    )
