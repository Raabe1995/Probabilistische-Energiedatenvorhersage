import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader, TensorDataset
import joblib

# 1. Daten laden & Säuberung
df = pd.read_csv('Realisierte_Erzeugung_Cleaned.csv', sep=';')
df['Timestamp'] = pd.to_datetime(df['Datum von'], dayfirst=True)
df.set_index('Timestamp', inplace=True)

# Datenlücken am Ende abschneiden
df = df[:'2026-04-17 12:00:00']

# Zyklische Zeit-Features
df['hour_sin'] = np.sin(2 * np.pi * df.index.hour / 24)
df['hour_cos'] = np.cos(2 * np.pi * df.index.hour / 24)

# Features & Target definieren
pv_col = 'Photovoltaik [MWh] Originalauflösungen'
feature_cols = [pv_col, 'hour_sin', 'hour_cos',
                'Wind Onshore [MWh] Originalauflösungen', 'Erdgas [MWh] Originalauflösungen']
target_col = [pv_col]

# Skalierung
scaler_features = MinMaxScaler()
scaler_target = MinMaxScaler()

scaled_features = scaler_features.fit_transform(df[feature_cols].values)
scaled_target = scaler_target.fit_transform(df[target_col].values)


# 2. Sequenzerstellung
def create_sequences(features, target, window_size):
    X, y = [], []
    for i in range(len(features) - window_size):
        X.append(features[i:i + window_size])
        y.append(target[i + window_size])
    return torch.FloatTensor(np.array(X)), torch.FloatTensor(np.array(y))


# 24 Stunden
window_size = 96
X, y = create_sequences(scaled_features, scaled_target, window_size)

# Split: 80% Train, 20% Test
train_size = int(len(X) * 0.8)
X_train_full, y_train_full = X[:train_size], y[:train_size]
X_test, y_test = X[train_size:], y[train_size:]

# Innerer Split für Validierung (Early Stopping)
val_size = int(len(X_train_full) * 0.1)
X_train, y_train = X_train_full[:-val_size], y_train_full[:-val_size]
X_val, y_val = X_train_full[-val_size:], y_train_full[-val_size:]

train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=32, shuffle=True)


# 3. Modell & Loss
class ProbabilisticRNN(nn.Module):
    def __init__(self, input_size, hidden_size=64, num_layers=2):
        super(ProbabilisticRNN, self).__init__()
        self.rnn = nn.RNN(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
        # 3 Quantile
        self.linear = nn.Linear(hidden_size, 3)

    def forward(self, x):
        # nn.RNN gibt nur out und den hidden state zurück
        out, _ = self.rnn(x)
        return self.linear(out[:, -1, :])


def pinball_loss(preds, target, quantiles):
    losses = []
    for i, q in enumerate(quantiles):
        error = target - preds[:, i:i + 1]
        losses.append(torch.max((q - 1) * error, q * error).mean())
    return sum(losses)


quantiles = [0.1, 0.5, 0.9]
model = ProbabilisticRNN(input_size=len(feature_cols)) # Instanziiert das RNN
optimizer = torch.optim.Adam(model.parameters(), lr=0.0005)

# Scheduler
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode='min',
    factor=0.5,
    patience=7
)

# 4. Optimierter Training Loop mit Early Stopping
epochs = 150
best_val_loss = float('inf')
patience = 15
counter = 0

history = {'train_loss': [], 'val_loss': []}

print("Starte RNN Training...")
for epoch in range(epochs):
    model.train()
    total_train_loss = 0
    for batch_X, batch_y in train_loader:
        optimizer.zero_grad()
        preds = model(batch_X)
        loss = pinball_loss(preds, batch_y, quantiles)
        loss.backward()
        optimizer.step()
        total_train_loss += loss.item()

    # Validierung
    model.eval()
    with torch.no_grad():
        val_preds = model(X_val)
        val_loss = pinball_loss(val_preds, y_val, quantiles)

    scheduler.step(val_loss)

    history['train_loss'].append(total_train_loss / len(train_loader))
    history['val_loss'].append(val_loss.item())

    if (epoch + 1) % 10 == 0:
        print(
            f'Epoch [{epoch + 1}/{epochs}] | Train Loss: {total_train_loss / len(train_loader):.5f} | Val Loss: {val_loss:.5f}')

    # Early Stopping Check
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        torch.save(model.state_dict(), 'best_prob_model_rnn.pth')
        counter = 0
    else:
        counter += 1
        if counter >= patience:
            print(f"Early Stopping in Epoche {epoch + 1}")
            break

# Bestes RNN Modell laden
model.load_state_dict(torch.load('best_prob_model_rnn.pth'))

# Grafische Anzeige des Lernverlaufs
plt.figure(figsize=(10, 5))
plt.plot(history['train_loss'], label='Train Loss')
plt.plot(history['val_loss'], label='Validation Loss')
plt.axvline(x=len(history['train_loss']) - patience - 1, color='r', linestyle='--', label='Bester Checkpoint')
plt.title('RNN Lernkurve (Loss Verlauf)')
plt.xlabel('Epoche')
plt.ylabel('Loss')
plt.legend()
plt.show()

# Struktur und Gewichte anzeigen
print("\n--- RNN Modell Struktur ---")
print(model)
weights = model.rnn.weight_ih_l0.data
print(f"Shape der Gewichte (Input-to-Hidden): {weights.shape}")

# 5. Evaluation & Metriken
model.eval()
with torch.no_grad():
    preds_test = model(X_test).numpy()
    preds_rescaled = [scaler_target.inverse_transform(preds_test[:, i:i + 1]) for i in range(3)]
    y_test_mwh = scaler_target.inverse_transform(y_test.numpy())

# PICP Metrik
within_bounds = (y_test_mwh.flatten() >= preds_rescaled[0].flatten()) & \
                (y_test_mwh.flatten() <= preds_rescaled[2].flatten())
picp = np.mean(within_bounds) * 100

print(f"\n--- RNN Modell Evaluation ---")
print(f"PICP (Abdeckung des 80% Intervalls): {picp:.2f}%")

from sklearn.metrics import mean_squared_error
median_rmse = np.sqrt(mean_squared_error(y_test_mwh, preds_rescaled[1]))
print(f"RNN Median RMSE (q0.5): {median_rmse:.2f} MWh")

# 6. Visualisierung
plt.figure(figsize=(15, 7))
plt.plot(y_test_mwh, label='Echte Erzeugung', color='black', alpha=0.6)
plt.plot(preds_rescaled[1], label='RNN Median Vorhersage (q0.5)', color='green', linestyle='--')
plt.fill_between(range(len(y_test_mwh)),
                 preds_rescaled[0].flatten(),
                 preds_rescaled[2].flatten(),
                 color='green', alpha=0.2, label='80% Unsicherheitsbereich (RNN)')
plt.title('Probabilistische Photovoltaik-Vorhersage (Multivariat mit RNN)')
plt.ylabel('MWh')
plt.legend()
plt.show()

# 7. Feature Importance (Permutation)
model.eval()
feature_importance = {}
baseline_loss = pinball_loss(model(X_test), y_test, quantiles).item()

for i, col in enumerate(feature_cols):
    X_test_permuted = X_test.clone()
    X_test_permuted[:, :, i] = X_test_permuted[torch.randperm(X_test.size(0)), :, i]

    with torch.no_grad():
        permuted_loss = pinball_loss(model(X_test_permuted), y_test, quantiles).item()
        feature_importance[col] = permuted_loss - baseline_loss

print("\n--- RNN Feature Importance (Einfluss auf Pinball Loss) ---")
for col, imp in sorted(feature_importance.items(), key=lambda x: x[1], reverse=True):
    print(f"{col}: {imp:.6f}")

# 8. Modell speichern
torch.save(model.state_dict(), 'final_probabilistic_rnn.pth')
joblib.dump(scaler_features, 'scaler_features_rnn.pkl')
joblib.dump(scaler_target, 'scaler_target_rnn.pkl')

print("\n--- Finales RNN Modell und Scaler wurden gesichert! ---")