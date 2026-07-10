#------------------------------------------------------------------------
#
# Probabilistische Energiedatenvorhersage
#
# Jan-Christian Raabe
#
#------------------------------------------------------------------------

#----------------------------
# EDA-Energieerzeugung
#----------------------------

# Indivdiduellen Arbeitspfad wählen
setwd("C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final")

# 1. Benötigte Bibliotheken laden
library(ggplot2)
library(readr)
library(dplyr)
library(scales)
# 2. Daten einlesen

file_path <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_15min/eda_energieerzeugung_daten_04_2026.csv"

# Semikolon (;) als Trennzeichen
df <- read_delim(file_path, delim = ";", show_col_types = FALSE)

# 3. Spaltennamen bereinigen & Zeitstempel konvertieren
colnames(df)[1] <- "Timestamp"
colnames(df)[2] <- "Photovoltaik"
colnames(df)[3] <- "Wind_Onshore"

# Zeitstempel in ein echtes POSIXct-Datetime-Objekt umwandeln
df$Timestamp <- as.POSIXct(df$Timestamp, format="%Y-%m-%d %H:%M:%S")

# 4. Daten ins "Long-Format" bringen (optimal für ggplot2)
df_long <- df %>%
  select(Timestamp, Photovoltaik, Wind_Onshore) %>%
  tidyr::pivot_longer(cols = c(Photovoltaik, Wind_Onshore), 
                      names_to = "Energiequelle", 
                      values_to = "Erzeugung_MWh")

# 5. Professionellen ggplot2-Plot erstellen
ggplot(df_long, aes(x = Timestamp, y = Erzeugung_MWh, color = Energiequelle)) +
  geom_line(size = 0.8, alpha = 0.8) +
  
  # Farben definieren (Passend zu Python-Plot: Orange für Solar, Blau für Wind)
  scale_color_manual(values = c("Photovoltaik" = "#E69F00", "Wind_Onshore" = "#0072B2"),
                     labels = c("Photovoltaik" = "Photovoltaik (Solar)", "Wind_Onshore" = "Wind Onshore")) +
  
  # Achsen- und Titelbeschriftung
  labs(
    title = "Realisierte Energieerzeugung (April 2026)",
    subtitle = "Visualisierung der SMARD-Zeitreihendaten für Solar und Wind Onshore",
    x = "Zeitverlauf",
    y = "Erzeugung (MWh)",
    color = "Energiequelle:"
  ) +
  
  # Zeitachse schön formatieren (z.B. alle 7 Tage ein Label im Format "Tag.Monat")
  scale_x_datetime(date_breaks = "7 days", date_labels = "%d.%m.") +
  scale_y_continuous(labels = comma_format(big.mark = ".", decimal.mark = ",")) +
  
  # Wissenschaftliches, sauberes Theme anwenden
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold", size = 14, margin = margin(b = 5)),
    plot.subtitle = element_text(face = "italic", color = "gray30", margin = margin(b = 15)),
    legend.position = "top",              # Legende nach oben setzen
    legend.title = element_text(face = "bold"),
    panel.grid.minor = element_blank(),   # Unwichtige Gitternetzlinien entfernen
    axis.title.x = element_text(margin = margin(t = 10)),
    axis.title.y = element_text(margin = margin(r = 10))
  )

# 6. Plot speichern
ggsave("r_plot_energieerzeugung_04_2026.png", width = 10, height = 5, dpi = 300)

#----------------------------
# EDA-Tagesprofil
#----------------------------

# 1. Benötigte Bibliotheken laden
library(ggplot2)
library(readr)
library(dplyr)
library(scales)

# 2. Daten einlesen mit absolutem Pfad
file_path_profile <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_15min/eda_tagesprofil_daten_04_2026.csv"

# CSV einlesen (Die erste Spalte enthält die Stunden 0-23 und heißt meist 'hour' oder 'Timestamp')
df_profile <- read_delim(file_path_profile, delim = ";", show_col_types = FALSE)

# Spaltennamen sauber umbenennen
# Spalte 1: Stunde, Spalte 2: Photovoltaik, Spalte 3: Wind Onshore
colnames(df_profile)[1] <- "Stunde"
colnames(df_profile)[2] <- "Photovoltaik"
colnames(df_profile)[3] <- "Wind_Onshore"

# 3. Daten ins "Long-Format" umstrukturieren
df_profile_long <- df_profile %>%
  tidyr::pivot_longer(cols = c(Photovoltaik, Wind_Onshore), 
                      names_to = "Energiequelle", 
                      values_to = "Durchschnitt_Erzeugung_MWh")

# 4. Professionellen Tagesprofil-Plot erstellen
ggplot(df_profile_long, aes(x = Stunde, y = Durchschnitt_Erzeugung_MWh, color = Energiequelle)) +
  # Etwas dickere Linie für das aggregierte Profil
  geom_line(size = 1.2, alpha = 0.9) +
  # Punkte auf den Stundenwerten für bessere Lesbarkeit
  geom_point(size = 2) +
  
  # Farbpalette
  scale_color_manual(values = c("Photovoltaik" = "#E69F00", "Wind_Onshore" = "#0072B2"),
                     labels = c("Photovoltaik" = "Photovoltaik (Solar)", "Wind_Onshore" = "Wind Onshore")) +
  
  # Achsenbeschriftung fixieren (X-Achse von 0 bis 23 Uhr im 2-Stunden-Takt)
  scale_x_continuous(breaks = seq(0, 23, by = 2), labels = paste0(seq(0, 23, by = 2), ":00")) +
  scale_y_continuous(labels = comma_format(big.mark = ".", decimal.mark = ",")) +
  
  # Titel und Labels
  labs(
    title = "Durchschnittliches Tagesprofil (April 2026)",
    subtitle = "Aggregierter Mittelwert der Erzeugung nach Uhrzeit",
    x = "Tageszeit (Uhr)",
    y = "Durchschnittliche Erzeugung (MWh)",
    color = "Energiequelle:"
  ) +
  
  # Wissenschaftliches Theme
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold", size = 14, margin = margin(b = 5)),
    plot.subtitle = element_text(face = "italic", color = "gray30", margin = margin(b = 15)),
    legend.position = "top",
    legend.title = element_text(face = "bold"),
    panel.grid.minor = element_blank(),
    axis.title.x = element_text(margin = margin(t = 10)),
    axis.title.y = element_text(margin = margin(r = 10))
  )

# 5. Plot speichern
ggsave("r_plot_tagesprofil_04_2026.png", width = 10, height = 5, dpi = 300)

#-----------------------------
# LSTM/RNN-Lernkurven - 15 min
#-----------------------------

# 1. Benötigte Bibliotheken laden
library(ggplot2)
library(readr)
library(dplyr)
library(tidyr)

# 2. LSTM-Lernkurve DIREKT über den Pfad einlesen
file_path_lstm <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_15min/lstm_lernkurve_daten_04_2026.csv"
df_lstm <- read_delim(file_path_lstm, delim = ";", show_col_types = FALSE)

# 3. RNN-Lernkurve DIREKT über den Pfad einlesen
file_path_rnn <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_15min/rnn_lernkurve_daten_04_2026.csv"
df_rnn <- read_delim(file_path_rnn, delim = ";", show_col_types = FALSE)

# 4. Daten für den Vergleich vorbereiten
df_lstm <- df_lstm %>% 
  mutate(Modell = "LSTM") %>%
  rename(Epoche = Epoch)

df_rnn <- df_rnn %>% 
  mutate(Modell = "RNN") %>%
  rename(Epoche = Epoch)

# Beide Datensätze untereinander zusammenführen (Merge)
df_all <- bind_rows(df_lstm, df_rnn)

# Daten ins "Long-Format" bringen, zur Trennung von 'train_loss' und 'val_loss'
df_long <- df_all %>%
  pivot_longer(cols = c(train_loss, val_loss),
               names_to = "Datensatz",
               values_to = "Loss") %>%
  mutate(
    Datensatz = recode(Datensatz, "train_loss" = "Training", "val_loss" = "Validierung"),
    Kurve = paste(Modell, Datensatz, sep = " - ")
  )

# 5. Professionellen Lernkurven-Plot erstellen
ggplot(df_long, aes(x = Epoche, y = Loss, color = Modell, linetype = Datensatz)) +
  geom_line(size = 1.0, alpha = 0.9) +
  
  scale_color_manual(values = c("LSTM" = "#0072B2", "RNN" = "#009E73")) +
  scale_linetype_manual(values = c("Training" = "solid", "Validierung" = "dashed")) +
  
  labs(
    title = "Vergleich der Lernkurven: LSTM vs. RNN",
    subtitle = "Verlauf des Pinball Loss über die Epochen (inkl. Early Stopping)",
    x = "Epoche",
    y = "Loss (Pinball Loss)",
    color = "Modellarchitektur:",
    linetype = "Daten-Split:"
  ) +
  
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold", size = 14, margin = margin(b = 5)),
    plot.subtitle = element_text(face = "italic", color = "gray30", margin = margin(b = 15)),
    legend.position = "top",
    legend.box = "horizontal",
    legend.title = element_text(face = "bold"),
    panel.grid.minor = element_blank(),
    axis.title.x = element_text(margin = margin(t = 10)),
    axis.title.y = element_text(margin = margin(r = 10))
  )

# 6. Plot speichern
ggsave("r_plot_lernkurven_vergleich.png", width = 10, height = 5, dpi = 300)

#--------------------------------------------------------------------------------------------------
# Probabilistischer Vorhersage-Plot: LSTM vs. RNN (Quantile & Unsicherheitsband) - 15 min Auflösung
#--------------------------------------------------------------------------------------------------

# 1. Benötigte Bibliotheken laden
library(ggplot2)
library(readr)
library(dplyr)
library(tidyr)
library(scales)

# 2. Pfade zu den Vorhersagedaten definieren
file_path_pred_lstm <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_15min/lstm_vorhersage_daten_04_2026.csv"
file_path_pred_rnn  <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_15min/rnn_vorhersage_daten_04_2026.csv"

# Sicherheits-Check
if (!file.exists(file_path_pred_lstm) | !file.exists(file_path_pred_rnn)) {
  stop("Eine oder beide Vorhersage-Dateien wurden nicht gefunden! Bitte Pfade prüfen.")
}

# 3. Daten einlesen
df_pred_lstm <- read_delim(file_path_pred_lstm, delim = ";", show_col_types = FALSE)
df_pred_rnn  <- read_delim(file_path_pred_rnn, delim = ";", show_col_types = FALSE)

# 4. Daten aufbereiten und zusammenführen
df_pred_lstm <- df_pred_lstm %>% 
  mutate(Index = row_number(), Modell = "LSTM")

df_pred_rnn <- df_pred_rnn %>% 
  mutate(Index = row_number(), Modell = "RNN")

# Kombinieren der beiden Datensätze
df_preds_all <- bind_rows(df_pred_lstm, df_pred_rnn)

# 5. Visualisierung mit ggplot2 (Facet-Grid für perfekten Vergleich)
ggplot(df_preds_all, aes(x = Index)) +
  
  # 80%-Unsicherheitsbereich (Füllung zwischen q0.1 und q0.9)
  geom_ribbon(aes(ymin = Quantil_0_1_MWh, ymax = Quantil_0_9_MWh, fill = Modell), alpha = 0.2) +
  
  # Echte Erzeugung (Schwarze, leicht transparente Linie im Hintergrund)
  geom_line(aes(y = Echte_Erzeugung_MWh, linetype = "Echte Erzeugung"), color = "black", size = 0.7, alpha = 0.6) +
  
  # Median-Vorhersage (q0.5) der Modelle
  geom_line(aes(y = Median_q0_5_MWh, color = Modell, linetype = "Median-Vorhersage (q0.5)"), size = 0.9) +
  
  # Farb- und Füllpaletten definieren (Blau für LSTM, Grün für RNN)
  scale_color_manual(values = c("LSTM" = "#0072B2", "RNN" = "#009E73")) +
  scale_fill_manual(values = c("LSTM" = "#0072B2", "RNN" = "#009E73")) +
  
  # Linientypen für die Legende explizit trennen
  scale_linetype_manual(name = "Daten-Typ:", values = c("Echte Erzeugung" = "solid", "Median-Vorhersage (q0.5)" = "dashed")) +
  
  # Tausendertrennzeichen für die Y-Achse formatieren
  scale_y_continuous(labels = comma_format(big.mark = ".", decimal.mark = ",")) +
  
  # Aufteilung in zwei übereinanderliegende Plots (LSTM oben, RNN unten) für maximale Übersicht
  facet_wrap(~Modell, ncol = 1) +
  
  # Achsenbeschriftungen und wissenschaftliche Titel
  labs(
    title = "Probabilistische Photovoltaik-Vorhersage im Vergleich",
    subtitle = "Echte Erzeugung vs. Median-Prognose mit 80%-Unsicherheitsbereich (q0.1 bis q0.9)",
    x = "Zeitschritte (15-Minuten-Intervalle)",
    y = "Erzeugung (MWh)",
    color = "Modellfarbe:",
    fill = "80%-Konfidenzband:"
  ) +
  
  # Wissenschaftliches Theme anwenden
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold", size = 14, margin = margin(b = 5)),
    plot.subtitle = element_text(face = "italic", color = "gray30", margin = margin(b = 15)),
    legend.position = "top",
    legend.box = "vertical",
    legend.title = element_text(face = "bold"),
    strip.background = element_rect(fill = "gray95", color = "gray80"), # Hintergrund der Modell-Labels
    strip.text = element_text(face = "bold", size = 11),
    panel.grid.minor = element_blank(),
    axis.title.x = element_text(margin = margin(t = 10)),
    axis.title.y = element_text(margin = margin(r = 10))
  )

# 6. Plot speichern
ggsave("r_plot_vorhersage_vergleich.png", width = 12, height = 7, dpi = 300)

#-----------------------------
# LSTM/RNN-Lernkurven - 60 min
#-----------------------------

# 1. Benötigte Bibliotheken laden
library(ggplot2)
library(readr)
library(dplyr)
library(tidyr)

# 2. LSTM-Lernkurve DIREKT über den Pfad einlesen
file_path_lstm <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_60min/lstm_lernkurve_daten_04_2026.csv"
df_lstm <- read_delim(file_path_lstm, delim = ";", show_col_types = FALSE)

# 3. RNN-Lernkurve DIREKT über den Pfad einlesen
file_path_rnn <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_60min/rnn_lernkurve_daten_04_2026.csv"
df_rnn <- read_delim(file_path_rnn, delim = ";", show_col_types = FALSE)

# 4. Daten für den Vergleich vorbereiten
df_lstm <- df_lstm %>% 
  mutate(Modell = "LSTM") %>%
  rename(Epoche = Epoch)

df_rnn <- df_rnn %>% 
  mutate(Modell = "RNN") %>%
  rename(Epoche = Epoch)

# Beide Datensätze untereinander zusammenführen (Merge)
df_all <- bind_rows(df_lstm, df_rnn)

# Daten ins "Long-Format" bringen, zur Trennung von 'train_loss' und 'val_loss'
df_long <- df_all %>%
  pivot_longer(cols = c(train_loss, val_loss),
               names_to = "Datensatz",
               values_to = "Loss") %>%
  mutate(
    Datensatz = recode(Datensatz, "train_loss" = "Training", "val_loss" = "Validierung"),
    Kurve = paste(Modell, Datensatz, sep = " - ")
  )

# 5. Professionellen Lernkurven-Plot erstellen
ggplot(df_long, aes(x = Epoche, y = Loss, color = Modell, linetype = Datensatz)) +
  geom_line(size = 1.0, alpha = 0.9) +
  
  scale_color_manual(values = c("LSTM" = "#0072B2", "RNN" = "#009E73")) +
  scale_linetype_manual(values = c("Training" = "solid", "Validierung" = "dashed")) +
  
  labs(
    title = "Vergleich der Lernkurven: LSTM vs. RNN",
    subtitle = "Verlauf des Pinball Loss über die Epochen (inkl. Early Stopping)",
    x = "Epoche",
    y = "Loss (Pinball Loss)",
    color = "Modellarchitektur:",
    linetype = "Daten-Split:"
  ) +
  
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold", size = 14, margin = margin(b = 5)),
    plot.subtitle = element_text(face = "italic", color = "gray30", margin = margin(b = 15)),
    legend.position = "top",
    legend.box = "horizontal",
    legend.title = element_text(face = "bold"),
    panel.grid.minor = element_blank(),
    axis.title.x = element_text(margin = margin(t = 10)),
    axis.title.y = element_text(margin = margin(r = 10))
  )

# 6. Plot speichern
ggsave("r_plot_lernkurven_vergleich.png", width = 10, height = 5, dpi = 300)

#--------------------------------------------------------------------------------------------------
# Probabilistischer Vorhersage-Plot: LSTM vs. RNN (Quantile & Unsicherheitsband) - 60 min Auflösung
#--------------------------------------------------------------------------------------------------

# 1. Benötigte Bibliotheken laden
library(ggplot2)
library(readr)
library(dplyr)
library(tidyr)
library(scales)

# 2. Pfade zu den Vorhersagedaten definieren
file_path_pred_lstm <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_60min/lstm_vorhersage_daten_04_2026.csv"
file_path_pred_rnn  <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_60min/rnn_vorhersage_daten_04_2026.csv"

# 3. Daten einlesen
df_pred_lstm <- read_delim(file_path_pred_lstm, delim = ";", show_col_types = FALSE)
df_pred_rnn  <- read_delim(file_path_pred_rnn, delim = ";", show_col_types = FALSE)

# 4. Daten aufbereiten und zusammenführen
df_pred_lstm <- df_pred_lstm %>% 
  mutate(Index = row_number(), Modell = "LSTM")

df_pred_rnn <- df_pred_rnn %>% 
  mutate(Index = row_number(), Modell = "RNN")

# Kombinieren der beiden Datensätze
df_preds_all <- bind_rows(df_pred_lstm, df_pred_rnn)

# 5. Visualisierung mit ggplot2 (In Variable 'final_plot' speichern)
final_plot <- ggplot(df_preds_all, aes(x = Index)) +
  geom_ribbon(aes(ymin = Quantil_0_1_MWh, ymax = Quantil_0_9_MWh, fill = Modell), alpha = 0.2) +
  geom_line(aes(y = Echte_Erzeugung_MWh, linetype = "Echte Erzeugung"), color = "black", size = 0.7, alpha = 0.6) +
  geom_line(aes(y = Median_q0_5_MWh, color = Modell, linetype = "Median-Vorhersage (q0.5)"), size = 0.9) +
  scale_color_manual(values = c("LSTM" = "#0072B2", "RNN" = "#009E73")) +
  scale_fill_manual(values = c("LSTM" = "#0072B2", "RNN" = "#009E73")) +
  scale_linetype_manual(name = "Daten-Typ:", values = c("Echte Erzeugung" = "solid", "Median-Vorhersage (q0.5)" = "dashed")) +
  scale_y_continuous(labels = comma_format(big.mark = ".", decimal.mark = ",")) +
  facet_wrap(~Modell, ncol = 1) +
  labs(
    title = "Probabilistische Photovoltaik-Vorhersage im Vergleich (60 min)",
    subtitle = "Echte Erzeugung vs. Median-Prognose mit 80%-Unsicherheitsbereich (q0.1 bis q0.9)",
    x = "Zeitschritte (60-Minuten-Intervalle)",
    y = "Erzeugung (MWh)",
    color = "Modellfarbe:",
    fill = "80%-Konfidenzband:"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold", size = 14, margin = margin(b = 5)),
    plot.subtitle = element_text(face = "italic", color = "gray30", margin = margin(b = 15)),
    legend.position = "top",
    legend.box = "vertical",
    legend.title = element_text(face = "bold"),
    strip.background = element_rect(fill = "gray95", color = "gray80"),
    strip.text = element_text(face = "bold", size = 11),
    panel.grid.minor = element_blank(),
    axis.title.x = element_text(margin = margin(t = 10)),
    axis.title.y = element_text(margin = margin(r = 10))
  )

# Zeigt den Plot im RStudio-Fenster an
print(final_plot)

# 6. Plot speichern
output_file_path <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/r_plot_vorhersage_vergleich_60min.png"

ggsave(
  filename = output_file_path, 
  plot = final_plot, 
  width = 12, 
  height = 7, 
  dpi = 300
)

print(paste("Grafik wurde erfolgreich hier abgelegt:", output_file_path))

#-----------------------------------------------
# LSTM/RNN-Lernkurven - 15 min längerer Zeitraum
#-----------------------------------------------

# 1. Benötigte Bibliotheken laden
library(ggplot2)
library(readr)
library(dplyr)
library(tidyr)

# 2. LSTM-Lernkurve DIREKT über den Pfad einlesen
file_path_lstm <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 01.03. bis 19.04.2026_15min/lstm_lernkurve_daten_03_2026_04_2026.csv"
df_lstm <- read_delim(file_path_lstm, delim = ";", show_col_types = FALSE)

# 3. RNN-Lernkurve DIREKT über den Pfad einlesen
file_path_rnn <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 01.03. bis 19.04.2026_15min/rnn_lernkurve_daten_03_2026_04_2026.csv"
df_rnn <- read_delim(file_path_rnn, delim = ";", show_col_types = FALSE)

# 4. Daten für den Vergleich vorbereiten
df_lstm <- df_lstm %>% 
  mutate(Modell = "LSTM") %>%
  rename(Epoche = Epoch)

df_rnn <- df_rnn %>% 
  mutate(Modell = "RNN") %>%
  rename(Epoche = Epoch)

# Beide Datensätze untereinander zusammenführen (Merge)
df_all <- bind_rows(df_lstm, df_rnn)

# Daten ins "Long-Format" bringen, zur Trennung von 'train_loss' und 'val_loss'
df_long <- df_all %>%
  pivot_longer(cols = c(train_loss, val_loss),
               names_to = "Datensatz",
               values_to = "Loss") %>%
  mutate(
    Datensatz = recode(Datensatz, "train_loss" = "Training", "val_loss" = "Validierung"),
    Kurve = paste(Modell, Datensatz, sep = " - ")
  )

# 5. Professionellen Lernkurven-Plot erstellen
ggplot(df_long, aes(x = Epoche, y = Loss, color = Modell, linetype = Datensatz)) +
  geom_line(size = 1.0, alpha = 0.9) +
  
  scale_color_manual(values = c("LSTM" = "#0072B2", "RNN" = "#009E73")) +
  scale_linetype_manual(values = c("Training" = "solid", "Validierung" = "dashed")) +
  
  labs(
    title = "Vergleich der Lernkurven: LSTM vs. RNN",
    subtitle = "Verlauf des Pinball Loss über die Epochen (inkl. Early Stopping)",
    x = "Epoche",
    y = "Loss (Pinball Loss)",
    color = "Modellarchitektur:",
    linetype = "Daten-Split:"
  ) +
  
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold", size = 14, margin = margin(b = 5)),
    plot.subtitle = element_text(face = "italic", color = "gray30", margin = margin(b = 15)),
    legend.position = "top",
    legend.box = "horizontal",
    legend.title = element_text(face = "bold"),
    panel.grid.minor = element_blank(),
    axis.title.x = element_text(margin = margin(t = 10)),
    axis.title.y = element_text(margin = margin(r = 10))
  )

# 6. Plot speichern
ggsave("r_plot_lernkurven_vergleich.png", width = 10, height = 5, dpi = 300)

#--------------------------------------------------------------------------------------------------------------------
# Probabilistischer Vorhersage-Plot: LSTM vs. RNN (Quantile & Unsicherheitsband) - 15 min Auflösung längerer Zeitraum
#--------------------------------------------------------------------------------------------------------------------

# 1. Benötigte Bibliotheken laden
library(ggplot2)
library(readr)
library(dplyr)
library(tidyr)
library(scales)

# 2. Pfade zu den Vorhersagedaten definieren
file_path_pred_lstm <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 01.03. bis 19.04.2026_15min/lstm_vorhersage_daten_03_2026_04_2026.csv"
file_path_pred_rnn  <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 01.03. bis 19.04.2026_15min/rnn_vorhersage_daten_03_2026_04_2026.csv"

# Sicherheits-Check vorab
if (!file.exists(file_path_pred_lstm) | !file.exists(file_path_pred_rnn)) {
  stop("Datei nicht gefunden! Bitte prüfe, ob die Dateien wirklich 'lstm_vorhersage_daten_...' heißen.")
}

# 3. Daten einlesen
df_pred_lstm <- read_delim(file_path_pred_lstm, delim = ";", show_col_types = FALSE)
df_pred_rnn  <- read_delim(file_path_pred_rnn, delim = ";", show_col_types = FALSE)

# 4. Daten aufbereiten, Spalten positionsbasiert auswählen/umbenennen und zusammenführen

df_pred_lstm <- df_pred_lstm %>% 
  # Schmeißt eventuelle leere Spalten ohne Namen raus und behält nur die echten Datenspalten
  select(where(~ !all(is.na(.)))) %>% 
  # Nimmt die letzten 4 Spalten (Index-unabhängig) und benennt sie exakt um
  setNames(tail(c("Index_Drop", "Echte_Erzeugung_MWh", "Quantil_0_1_MWh", "Median_q0_5_MWh", "Quantil_0_9_MWh"), ncol(.))) %>% 
  select(Echte_Erzeugung_MWh, Quantil_0_1_MWh, Median_q0_5_MWh, Quantil_0_9_MWh) %>% 
  mutate(Index = row_number(), Modell = "LSTM")

df_pred_rnn <- df_pred_rnn %>% 
  select(where(~ !all(is.na(.)))) %>% 
  setNames(tail(c("Index_Drop", "Echte_Erzeugung_MWh", "Quantil_0_1_MWh", "Median_q0_5_MWh", "Quantil_0_9_MWh"), ncol(.))) %>% 
  select(Echte_Erzeugung_MWh, Quantil_0_1_MWh, Median_q0_5_MWh, Quantil_0_9_MWh) %>% 
  mutate(Index = row_number(), Modell = "RNN")

# Kombinieren der beiden Datensätze (Jetzt garantiert ohne Struktur-Konflikte)
df_preds_all <- bind_rows(df_pred_lstm, df_pred_rnn)

# 5. Visualisierung mit ggplot2 (Beschriftungen auf 15-min-Auflösung und korrekten Speicherpfad angepasst)
final_plot <- ggplot(df_preds_all, aes(x = Index)) +
  geom_ribbon(aes(ymin = Quantil_0_1_MWh, ymax = Quantil_0_9_MWh, fill = Modell), alpha = 0.2) +
  geom_line(aes(y = Echte_Erzeugung_MWh, linetype = "Echte Erzeugung"), color = "black", size = 0.7, alpha = 0.6) +
  geom_line(aes(y = Median_q0_5_MWh, color = Modell, linetype = "Median-Vorhersage (q0.5)"), size = 0.9) +
  scale_color_manual(values = c("LSTM" = "#0072B2", "RNN" = "#009E73")) +
  scale_fill_manual(values = c("LSTM" = "#0072B2", "RNN" = "#009E73")) +
  scale_linetype_manual(name = "Daten-Typ:", values = c("Echte Erzeugung" = "solid", "Median-Vorhersage (q0.5)" = "dashed")) +
  scale_y_continuous(labels = comma_format(big.mark = ".", decimal.mark = ",")) +
  facet_wrap(~Modell, ncol = 1) +
  labs(
    title = "Probabilistische Photovoltaik-Vorhersage im Vergleich (März - April 2026)",
    subtitle = "Echte Erzeugung vs. Median-Prognose mit 80%-Unsicherheitsbereich (15-Minuten-Auflösung)",
    x = "Zeitschritte (15-Minuten-Intervalle)",
    y = "Erzeugung (MWh)",
    color = "Modellfarbe:",
    fill = "80%-Konfidenzband:"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold", size = 14, margin = margin(b = 5)),
    plot.subtitle = element_text(face = "italic", color = "gray30", margin = margin(b = 15)),
    legend.position = "top",
    legend.box = "vertical",
    legend.title = element_text(face = "bold"),
    strip.background = element_rect(fill = "gray95", color = "gray80"),
    strip.text = element_text(face = "bold", size = 11),
    panel.grid.minor = element_blank(),
    axis.title.x = element_text(margin = margin(t = 10)),
    axis.title.y = element_text(margin = margin(r = 10))
  )

# Zeigt den Plot im RStudio-Fenster an
print(final_plot)

# 6. Plot speichern
output_file_path <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/r_plot_vorhersage_vergleich_15min_langzeit.png"

ggsave(
  filename = output_file_path, 
  plot = final_plot, 
  width = 12, 
  height = 7, 
  dpi = 300
)

print(paste("Grafik wurde erfolgreich hier abgelegt:", output_file_path))

#===============================================================================
# ARCHITEKTURVERGLEICH DER LERNKURVEN (LSTM VS. RNN)
#===============================================================================

# 1. Benötigte Bibliotheken laden
library(readr)
library(dplyr)
library(tidyr)
library(ggplot2)

# 2. Absolute Pfade zu den CSV-Dateien definieren
path_lk_15m_kurz <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_15min/lstm_lernkurve_daten_04_2026.csv"
path_rk_15m_kurz <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_15min/rnn_lernkurve_daten_04_2026.csv"

path_lk_60m_kurz <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_60min/lstm_lernkurve_daten_04_2026.csv"
path_rk_60m_kurz <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_60min/rnn_lernkurve_daten_04_2026.csv"

path_lk_15m_lang  <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 01.03. bis 19.04.2026_15min/lstm_lernkurve_daten_03_2026_04_2026.csv"
path_rk_15m_lang  <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 01.03. bis 19.04.2026_15min/rnn_lernkurve_daten_03_2026_04_2026.csv"

# Sicherheits-Check: Prüfen, ob alle Dateien existieren
all_paths <- c(path_lk_15m_kurz, path_rk_15m_kurz, path_lk_60m_kurz, path_rk_60m_kurz, path_lk_15m_lang, path_rk_15m_lang)
if (!all(file.exists(all_paths))) {
  stop("Mindestens eine Lernkurven-CSV wurde nicht gefunden! Bitte die Pfade überprüfen.")
}

# 3. Hilfsfunktion zum sauberen Laden und Labeln der Datensätze
load_lk <- function(path, modell, setup) {
  read_delim(path, delim = ";", show_col_types = FALSE) %>%
    mutate(Modell = modell, Setup = setup) %>%
    rename(Epoche = Epoch)
}

# 4. Daten laden, zusammenführen und ins Long-Format konvertieren
df_lk_all <- bind_rows(
  load_lk(path_lk_15m_kurz, "LSTM", "15 Min (April)"),
  load_lk(path_rk_15m_kurz, "RNN",  "15 Min (April)"),
  load_lk(path_lk_60m_kurz, "LSTM", "60 Min (April)"),
  load_lk(path_rk_60m_kurz, "RNN",  "60 Min (April)"),
  load_lk(path_lk_15m_lang,  "LSTM", "15 Min (März-April)"),
  load_lk(path_rk_15m_lang,  "RNN",  "15 Min (März-April)")
) %>%
  pivot_longer(cols = c(train_loss, val_loss), names_to = "Datensatz", values_to = "Loss") %>%
  mutate(
    # Spalteninhalte eindeutschen
    Datensatz = case_when(
      Datensatz == "train_loss" ~ "Training",
      Datensatz == "val_loss"   ~ "Validierung"
    ),
    # Gruppen-ID für ggplot zur exakten Trennung der Linienverläufe innerhalb der Facetten
    Kurven_ID = paste(Setup, Datensatz, sep = " - ")
  )

# 5. Geteilten Plot erstellen (Nebeneinander: LSTM vs. RNN)
plot_split_architecture <- ggplot(df_lk_all, aes(x = Epoche, y = Loss, 
                                                 color = Setup, 
                                                 linetype = Datensatz, 
                                                 alpha = Datensatz,
                                                 group = Kurven_ID)) +
  # Linienstärke für optimale Sichtbarkeit leicht erhöht
  geom_line(size = 1.1) +
  
  # Kontrastreiche, wissenschaftliche Farbpalette für die 3 Szenarien
  scale_color_manual(values = c(
    "15 Min (April)"       = "#D55E00", # Rotorange
    "60 Min (April)"       = "#0072B2", # Tiefblau
    "15 Min (März-April)"  = "#CC79A7"  # Edles Lila/Rosa
  )) +
  
  # Linientypen: Training fein gestrichelt, Validierung durchgezogen im Fokus
  scale_linetype_manual(values = c("Training" = "dotdash", "Validierung" = "solid")) +
  
  # Transparenz: Validierung voll sichtbar (1.0), Training dezent im Hintergrund (0.40)
  scale_alpha_manual(values = c("Training" = 0.40, "Validierung" = 1.0)) +
  
  # Trennung der Grafiken in zwei Spalten (Links LSTM, Rechts RNN)
  facet_wrap(~Modell, ncol = 2) +
  
  # Titel und Legendenbeschriftungen (Identische Namen für linetype und alpha führt sie zusammen)
  labs(
    title = "Verlustkurven im Architekturvergleich (Pinball Loss)",
    subtitle = "Direkte Gegenüberstellung von LSTM und RNN",
    x = "Epoche",
    y = "Loss (Pinball Loss)",
    color = "Datensatz-Szenario:",
    linetype = "Daten-Split:",
    alpha = "Daten-Split:"
  ) +
  
  # Wissenschaftliches Feintuning des Layouts
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold", size = 14, margin = margin(b = 5)),
    plot.subtitle = element_text(face = "italic", color = "gray30", margin = margin(b = 15)),
    legend.position = "top", 
    legend.box = "vertical",           # Legenden sauber untereinander stapeln
    
    # --- GEÄNDERT: LEGENDE KLEINER GESTALTEN ---
    legend.title = element_text(face = "bold", size = 9),  # Titel kleiner (vorher Standard)
    legend.text = element_text(size = 8.5),                # Text kleiner (vorher Standard)
    legend.key.size = unit(0.4, "cm"),                    # Größe der farbigen Quadrate/Linien reduzieren
    legend.spacing.y = unit(0.05, "cm"),                  # Vertikalen Abstand zwischen den Boxen verringern
    # -------------------------------------------
    
    strip.background = element_rect(fill = "gray95", color = "gray80"), # Design der Fenster-Überschriften
    strip.text = element_text(face = "bold", size = 12),                # Textgröße für "LSTM" & "RNN"
    panel.grid.minor = element_blank(),                                 # Unwichtige Gitternetzlinien ausblenden
    axis.title.x = element_text(margin = margin(t = 10)),
    axis.title.y = element_text(margin = margin(r = 10))
  )

# 6. Plot im RStudio-Plot-Fenster ausgeben
print(plot_split_architecture)

# 7. Grafik hochauflösend speichern (Pfad nutzt das gesetzte Arbeitsverzeichnis deiner Session)
output_filename <- "r_plot_LERNKURVEN_nach_architektur_getrennt.png"
ggsave(
  filename = output_filename, 
  plot = plot_split_architecture, 
  width = 14, 
  height = 6, 
  dpi = 300
)

print(paste("Die Grafik wurde erfolgreich unter folgendem Namen gespeichert:", output_filename))

#===============================================================================
# PREDICTION-VERGLEICH (NORMIERT & FARBOPTIMIERT)
#===============================================================================

# 1. Benötigte Bibliotheken laden
library(ggplot2)
library(readr)
library(dplyr)
library(tidyr)
library(scales)

# 2. Absolute Pfade definieren
path_lstm_15m <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_15min/lstm_vorhersage_daten_04_2026.csv"
path_rnn_15m  <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_15min/rnn_vorhersage_daten_04_2026.csv"

path_lstm_60m <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_60min/lstm_vorhersage_daten_04_2026.csv"
path_rnn_60m  <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_60min/rnn_vorhersage_daten_04_2026.csv"

path_lstm_lang <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 01.03. bis 19.04.2026_15min/lstm_vorhersage_daten_03_2026_04_2026.csv"
path_rnn_lang  <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 01.03. bis 19.04.2026_15min/rnn_vorhersage_daten_03_2026_04_2026.csv"

# 3. Hilfsfunktion zur Erstellung der Zeitachse und Bereinigung
load_and_time_assign <- function(path, modell, szenario, interval_min) {
  df <- read_delim(path, delim = ";", show_col_types = FALSE) %>% 
    select(where(~ !all(is.na(.))))
  
  if(ncol(df) >= 4) {
    df <- df %>% 
      setNames(tail(c("Index_Drop", "Echte_Erzeugung", "q0_1", "Median", "q0_9"), ncol(.))) %>% 
      select(Echte_Erzeugung, q0_1, Median, q0_9)
  }
  
  start_time <- as.POSIXct("2026-04-09 00:00:00", tz = "UTC")
  
  df <- df %>% 
    mutate(
      Modell = modell,
      Szenario = szenario,
      Timestamp = start_time + (row_number() - 1) * (interval_min * 60)
    )
  
  df <- df %>% 
    filter(Timestamp >= as.POSIXct("2026-04-09 00:00:00", tz = "UTC") & 
             Timestamp <= as.POSIXct("2026-04-19 23:45:00", tz = "UTC"))
  
  return(df)
}

# 4. Alle Daten laden
df_all_preds <- bind_rows(
  load_and_time_assign(path_lstm_15m, "LSTM", "15 Min (April)", 15),
  load_and_time_assign(path_rnn_15m,  "RNN",  "15 Min (April)", 15),
  load_and_time_assign(path_lstm_60m, "LSTM", "60 Min (April)", 60),
  load_and_time_assign(path_rnn_60m,  "RNN",  "60 Min (April)", 60),
  load_and_time_assign(path_lstm_lang, "LSTM", "15 Min (März-April)", 15),
  load_and_time_assign(path_rnn_lang,  "RNN",  "15 Min (März-April)", 15)
)

# --- NEU: MIN-MAX NORMIERUNG AUF [0, 1] ---
# Wir ermitteln das globale Minimum und Maximum der echten Erzeugung, um alle Werte einheitlich zu skalieren
min_val <- min(df_all_preds$Echte_Erzeugung, na.rm = TRUE)
max_val <- max(df_all_preds$Echte_Erzeugung, na.rm = TRUE)

df_all_preds <- df_all_preds %>% 
  mutate(
    Echte_Erzeugung = (Echte_Erzeugung - min_val) / (max_val - min_val),
    q0_1            = (q0_1 - min_val) / (max_val - min_val),
    Median          = (Median - min_val) / (max_val - min_val),
    q0_9            = (q0_9 - min_val) / (max_val - min_val)
  )

# --- OPTIMIERTE FARBPALETTE (Wissenschaftlich, kontrastreich & harmonisch) ---
colors_szenarios <- c(
  "15 Min (April)"       = "#1b9e77", # Dunkles Smaragdgrün
  "60 Min (April)"       = "#d95f02", # Kräftiges Orange
  "15 Min (März-April)"  = "#7570b3"  # Schieferblau/Violett
)

# Gemeinsame Theme-Funktion für kleine Legenden und sauberes Design
theme_probabilistic <- function() {
  theme_minimal(base_size = 12) +
    theme(
      plot.title = element_text(face = "bold", size = 14, margin = margin(b = 5)),
      plot.subtitle = element_text(face = "italic", color = "gray30", margin = margin(b = 15)),
      legend.position = "top",
      legend.box = "vertical",
      legend.spacing.y = unit(0.02, "cm"),
      
      # --- LEGENDE COMPACT ---
      legend.title = element_text(face = "bold", size = 9),
      legend.text = element_text(size = 8.5),
      legend.key.size = unit(0.35, "cm"),
      # -----------------------
      
      panel.grid.minor = element_blank(),
      axis.title.x = element_text(margin = margin(t = 10)),
      axis.title.y = element_text(margin = margin(r = 10))
    )
}

#===============================================================================
# PLOT 1: LSTM - Vergleich der 3 Szenarien (Normiert)
#===============================================================================
df_lstm_plots <- df_all_preds %>% filter(Modell == "LSTM")

plot_lstm <- ggplot(df_lstm_plots, aes(x = Timestamp)) +
  geom_ribbon(aes(ymin = q0_1, ymax = q0_9, fill = Szenario), alpha = 0.12) + # Alpha leicht gesenkt für bessere Überlagerung
  geom_line(data = filter(df_lstm_plots, Szenario == "15 Min (April)"), 
            aes(y = Echte_Erzeugung, linetype = "Echte Erzeugung"), color = "#222222", size = 0.7, alpha = 0.6) +
  geom_line(aes(y = Median, color = Szenario, linetype = "Median-Vorhersage (q0.5)"), size = 0.8) +
  
  scale_color_manual(values = colors_szenarios) +
  scale_fill_manual(values = colors_szenarios) +
  scale_linetype_manual(name = "Daten-Typ:", values = c("Echte Erzeugung" = "solid", "Median-Vorhersage (q0.5)" = "dashed")) +
  
  scale_x_datetime(date_breaks = "2 days", date_labels = "%d.%m.") +
  scale_y_continuous(labels = number_format(accuracy = 0.1)) + # Formatierung für Werte zwischen 0 und 1
  
  labs(
    title = "Probabilistischer Modellvergleich: LSTM-Szenarien (Normiert)",
    subtitle = "Min-Max-normierter Vergleich [0, 1] im Zeitraum 09. bis 19.04.2026",
    x = "Zeitverlauf",
    y = "Normierte Erzeugung (Skala 0-1)",
    color = "Modell-Szenario:",
    fill = "80%-Konfidenzband:"
  ) +
  theme_probabilistic()

ggsave("r_plot_vorhersage_vergleich_LSTM_Szenarien_normiert.png", plot = plot_lstm, width = 12, height = 6, dpi = 300)


#===============================================================================
# PLOT 2: RNN - Vergleich der 3 Szenarien (Normiert)
#===============================================================================
df_rnn_plots <- df_all_preds %>% filter(Modell == "RNN")

plot_rnn <- ggplot(df_rnn_plots, aes(x = Timestamp)) +
  geom_ribbon(aes(ymin = q0_1, ymax = q0_9, fill = Szenario), alpha = 0.12) +
  geom_line(data = filter(df_rnn_plots, Szenario == "15 Min (April)"), 
            aes(y = Echte_Erzeugung, linetype = "Echte Erzeugung"), color = "#222222", size = 0.7, alpha = 0.6) +
  geom_line(aes(y = Median, color = Szenario, linetype = "Median-Vorhersage (q0.5)"), size = 0.8) +
  
  scale_color_manual(values = colors_szenarios) +
  scale_fill_manual(values = colors_szenarios) +
  scale_linetype_manual(name = "Daten-Typ:", values = c("Echte Erzeugung" = "solid", "Median-Vorhersage (q0.5)" = "dashed")) +
  
  scale_x_datetime(date_breaks = "2 days", date_labels = "%d.%m.") +
  scale_y_continuous(labels = number_format(accuracy = 0.1)) +
  
  labs(
    title = "Probabilistischer Modellvergleich: RNN-Szenarien (Normiert)",
    subtitle = "Min-Max-normierter Vergleich [0, 1] im Zeitraum 09. bis 19.04.2026",
    x = "Zeitverlauf",
    y = "Normierte Erzeugung (Skala 0-1)",
    color = "Modell-Szenario:",
    fill = "80%-Konfidenzband:"
  ) +
  theme_probabilistic()

ggsave("r_plot_vorhersage_vergleich_RNN_Szenarien_normiert.png", plot = plot_rnn, width = 12, height = 6, dpi = 300)

print("Beide normierten Grafiken wurden erfolgreich mit der neuen Farbpalette gespeichert!")