# Entwicklung eines probabilistischen LSTM-Modells zur Vorhersage von Photovoltaik-Einspeisung auf Basis von SMARD-Marktdaten
## Technische Schwerpunkte
LSTM, Neuronales Netz
## Welches Problem soll das Projekt lösen?
Das Projekt löst das Problem der Planungsunsicherheit bei volatilen, erneuerbaren Energien (speziell Photovoltaik). Das Kernproblem: Herkömmliche statistische Modelle liefern oft nur eine starre Punktprognose. Liegt das Modell wetterbedingt (z. B. durch plötzliche Bewölkung) daneben, müssen Netzbetreiber in Sekundenschnelle extrem teure Ausgleichsenergie einkaufen, um einen Blackout zu verhindern. Die Lösung des Projekts: Durch den Einsatz eines probabilistischen Multivariaten LSTMs berechnet das Modell über eine Quantils-Regression (Pinball Loss) einen dynamischen Sicherheitskorridor (80%-Konfidenzintervall). Der Netzbetreiber sieht sofort, wie sicher sich die KI bei der Prognose ist, und kann das finanzielle Risiko präzise managen.

## Interesse und Motivation
Das Modell ist multivariat und lernt die physikalischen Wechselwirkungen im Stromnetz, indem es Windkraft-Einspeisung, fossiles Erdgas und den zyklischen Tagesverlauf (mittels Sinus-/Cosinus-Transformationen) miteinander fusioniert. Permutation Feature Importance: Dadurch wird mathematisch messbar und für den Menschen transparent gemacht, welche Faktoren (z. B. die Tageszeit oder die Windlast) gerade den größten Einfluss auf die Solarprognose haben. Das schafft das notwendige Vertrauen für den echten Handelseinsatz.

## Was soll am Ende demonstriert werden?
Es wird demonstriert, wie die KI im Vergleich zur Realität (den Ist-Werten des Netzes) abschneidet. Es wird live gezeigt, wie sich das Unsicherheitsband bei wechselhaftem Wetter ausdehnt und bei stabilen Wetterlagen verengt (hohe Planungssicherheit).

## Link zu den SMARD-Marktdaten
https://www.smard.de/home/downloadcenter/download-marktdaten/?downloadAttributes=%7B%22selectedCategory%22:1,%22selectedSubCategory%22:1,%22selectedRegion%22:false,%22selectedFileType%22:%22CSV%22,%22from%22:1775685600000,%22to%22:1776635999999%7D
