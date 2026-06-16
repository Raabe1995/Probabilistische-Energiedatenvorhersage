#------------------------------------------------------------------------
# Probabilistische Energiedatenvorhersage
# 
# Konzepte des Machine Learnings
#
# Jan-Christian Raabe
# FH Wedel
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

# 6. Plot in hoher Qualität speichern (optional)
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
  
  # Farbpalette (Synchron zu deinem ersten Plot)
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

# 5. Plot speichern (optional)
ggsave("r_plot_tagesprofil_04_2026.png", width = 10, height = 5, dpi = 300)

#-----------------------------
# LSTM/RNN-Lernkurven - 15 min
#-----------------------------

# 1. Benötigte Bibliotheken laden
library(ggplot2)
library(readr)
library(dplyr)
library(tidyr)

# 2. LSTM-Lernkurve DIREKT über den Pfad einlesen (OHNE file.choose!)
file_path_lstm <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_15min/lstm_lernkurve_daten_04_2026.csv"
df_lstm <- read_delim(file_path_lstm, delim = ";", show_col_types = FALSE)

# 3. RNN-Lernkurve DIREKT über den Pfad einlesen (OHNE file.choose!)
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

# 6. Plot in hoher Qualität speichern
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
# Wir fügen eine Index-Spalte für den zeitlichen Verlauf hinzu (da die CSVs Zeilenindizes haben)
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

# 6. Plot hochauflösend für das Dokument speichern
ggsave("r_plot_vorhersage_vergleich.png", width = 12, height = 7, dpi = 300)

#-----------------------------
# LSTM/RNN-Lernkurven - 60 min
#-----------------------------

# 1. Benötigte Bibliotheken laden
library(ggplot2)
library(readr)
library(dplyr)
library(tidyr)

# 2. LSTM-Lernkurve DIREKT über den Pfad einlesen (OHNE file.choose!)
file_path_lstm <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 09. bis 19.04.2026_60min/lstm_lernkurve_daten_04_2026.csv"
df_lstm <- read_delim(file_path_lstm, delim = ";", show_col_types = FALSE)

# 3. RNN-Lernkurve DIREKT über den Pfad einlesen (OHNE file.choose!)
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

# 6. Plot in hoher Qualität speichern
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

# 6. Plot hochauflösend direkt im Zielordner ablegen
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

# 2. LSTM-Lernkurve DIREKT über den Pfad einlesen (OHNE file.choose!)
file_path_lstm <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/Daten 01.03. bis 19.04.2026_15min/lstm_lernkurve_daten_03_2026_04_2026.csv"
df_lstm <- read_delim(file_path_lstm, delim = ";", show_col_types = FALSE)

# 3. RNN-Lernkurve DIREKT über den Pfad einlesen (OHNE file.choose!)
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

# 6. Plot in hoher Qualität speichern
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

# 2. Pfade zu den Vorhersagedaten definieren (KORRIGIERT: vorhersage statt lernkurve)
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
# Wir greifen uns gezielt die letzten 4 Spalten, um eine eventuelle leere Index-Spalte zu ignorieren.

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

# 6. Plot hochauflösend im Hauptordner 'Final' ablegen (KORRIGIERT: Name spiegelt 15min wider)
output_file_path <- "C:/Users/jan-c/Desktop/Probabilistische-Energiedatenvorhersage/smard_daten/output/Alle/Final/r_plot_vorhersage_vergleich_15min_langzeit.png"

ggsave(
  filename = output_file_path, 
  plot = final_plot, 
  width = 12, 
  height = 7, 
  dpi = 300
)

print(paste("Grafik wurde erfolgreich hier abgelegt:", output_file_path))