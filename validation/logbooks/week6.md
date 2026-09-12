# Testing BLE LE 1M generated from `gen_bluetooth.m`

- Original test run with BLE LE 1M generated samples from `gen_bluetooth.m`:

```python
─── burst 11  t=5.966 ms  len=0.268 ms  SNR≈198.1 dB ───
  class          fsk2
  BW99 / RMS     1.226 MHz / 501 kHz   offset -8.772 kHz
  env CV / PAPR  0.000 / 0.0 dB   flatness 0.69  edge 19.7 dB
  symbol rate    1 MHz (line SNR 15113404.6x)
  FSK tones      2, deviation 649.6 kHz
  CSS            BW≈1.226 MHz, SF≈5, 4.698e+04 MHz/s, dechirp energy 0.11
  · symbol rate from squared-envelope
  · tone count via eye(w=2)
  candidates:
     57.8%  Bluetooth LE 2M (GFSK)
            spec: Bluetooth Core 5.4
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 1.226 MHz vs 1.6 MHz–2.6 MHz: 0.62
            · symbol rate 1 MHz vs 1.8 MHz–2.2 MHz: 0.29
            · burst 0.268 ms: 0.96
            · FSK deviation 649.6 kHz: 0.76
     27.4%  Bluetooth Classic (GFSK, BR)
            spec: Bluetooth Core 5.4, Vol 6
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 1.226 MHz vs 700 kHz–1.3 MHz: 1.00
            · symbol rate 1 MHz vs 850 kHz–1.15 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 649.6 kHz: 0.00
     27.4%  Bluetooth LE 1M (GFSK)
            spec: Bluetooth Core 5.4, Vol 6 Part B
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 1.226 MHz vs 800 kHz–1.4 MHz: 1.00
            · symbol rate 1 MHz vs 900 kHz–1.1 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 649.6 kHz: 0.00
  * burst 0     0.27 ms  snr 198.1 dB  cv  0.00  score 0.60  Bluetooth LE 2M (GFSK)
  * burst 1     0.27 ms  snr 198.1 dB  cv  0.00  score 0.58  Bluetooth LE 2M (GFSK)
  * burst 2     0.27 ms  snr 198.1 dB  cv  0.00  score 0.62  Bluetooth LE 2M (GFSK)
  * burst 3     0.27 ms  snr 198.1 dB  cv  0.00  score 0.58  Bluetooth LE 2M (GFSK)
  * burst 4     0.27 ms  snr 198.1 dB  cv  0.00  score 0.59  Bluetooth LE 2M (GFSK)
  * burst 5     0.27 ms  snr 198.1 dB  cv  0.00  score 0.58  Bluetooth LE 2M (GFSK)
  * burst 6     0.27 ms  snr 198.1 dB  cv  0.00  score 0.57  Bluetooth LE 2M (GFSK)
  * burst 7     0.27 ms  snr 198.1 dB  cv  0.00  score 0.62  Bluetooth LE 2M (GFSK)
  * burst 8     0.27 ms  snr 198.1 dB  cv  0.00  score 0.59  Bluetooth LE 2M (GFSK)
  * burst 9     0.27 ms  snr 198.1 dB  cv  0.00  score 0.59  Bluetooth LE 2M (GFSK)
  * burst 10    0.27 ms  snr 198.1 dB  cv  0.00  score 0.61  Bluetooth LE 2M (GFSK)
  * burst 11    0.27 ms  snr 198.1 dB  cv  0.00  score 0.58  Bluetooth LE 2M (GFSK)
  -> 12 bursts, 12 confident. missed (wanted Bluetooth LE 1M)

======================================================================
SUMMARY
======================================================================
band        bursts  conf  result
bluetooth_le1m_clean      12    12  missed (wanted Bluetooth LE 1M)
```

- Noticed that detector was incorrectly pulling FSK deviation of around ~500 kHz when ~250 kHz was expected.

    - This lined up with matching Bluetooth LE 2M - the FSK deviation was off.

    - Altered `iq_protocol_id.py` from Philip's Claude script to half deviation calculation.

    - Claude's script was initially using tone-tone separation instead of single-sided deviation which caused the LE1M -> LE2M errors. This one's an easy fix.

```python
# before
dev = float(tones[1] - tones[0]) if n == 2 else (float(np.median(d)) if d.size else 0.0)

# after
dev = 0.5*float(tones[1] - tones[0]) if n == 2 else (float(np.median(d)) if d.size else 0.0)
```

- After changing deviation calculation:

```python
(.venv) petervertsonis@Peters-MacBook-Pro thesis % python validation/experiments/run_sweep_id.py --dir generated

======================================================================
bluetooth_le1m_clean  --  2402.000 MHz, 79360 samples @ 8.0 MS/s
expected: Bluetooth LE 1M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================
  * burst 0     0.27 ms  snr 198.1 dB  cv  0.00  score 0.99  Bluetooth LE 1M (GFSK)
  * burst 1     0.27 ms  snr 198.1 dB  cv  0.00  score 0.95  Bluetooth LE 1M (GFSK)
  * burst 2     0.27 ms  snr 198.1 dB  cv  0.00  score 0.99  Bluetooth LE 1M (GFSK)
  * burst 3     0.27 ms  snr 198.1 dB  cv  0.00  score 0.95  Bluetooth LE 1M (GFSK)
  * burst 4     0.27 ms  snr 198.1 dB  cv  0.00  score 0.95  Bluetooth LE 1M (GFSK)
  * burst 5     0.27 ms  snr 198.1 dB  cv  0.00  score 0.95  Bluetooth LE 1M (GFSK)
  * burst 6     0.27 ms  snr 198.1 dB  cv  0.00  score 0.95  Bluetooth LE 1M (GFSK)
  * burst 7     0.27 ms  snr 198.1 dB  cv  0.00  score 0.99  Bluetooth LE 1M (GFSK)
  * burst 8     0.27 ms  snr 198.1 dB  cv  0.00  score 0.95  Bluetooth LE 1M (GFSK)
  * burst 9     0.27 ms  snr 198.1 dB  cv  0.00  score 0.95  Bluetooth LE 1M (GFSK)
  * burst 10    0.27 ms  snr 198.1 dB  cv  0.00  score 0.99  Bluetooth LE 1M (GFSK)
  * burst 11    0.27 ms  snr 198.1 dB  cv  0.00  score 0.95  Bluetooth LE 1M (GFSK)
  -> 12 bursts, 12 confident. CORRECT

======================================================================
bluetooth_le1m_snr+00  --  2402.000 MHz, 79360 samples @ 8.0 MS/s
expected: Bluetooth LE 1M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================
    burst 0     9.92 ms  snr   2.5 dB  cv  0.52  score 0.20  LTE / 5G NR downlink (OFDM, 15 kHz SCS)
  -> 1 bursts, 0 confident. missed (wanted Bluetooth LE 1M)

======================================================================
bluetooth_le1m_snr+05  --  2402.000 MHz, 79360 samples @ 8.0 MS/s
expected: Bluetooth LE 1M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================
    burst 0     0.13 ms  snr   6.7 dB  cv  0.35  score 0.24  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 1     0.09 ms  snr   6.8 dB  cv  0.36  score 0.27  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 2     0.11 ms  snr   6.7 dB  cv  0.34  score 0.25  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 3     0.08 ms  snr   6.8 dB  cv  0.34  score 0.29  Wi-Fi 802.11b/g (DSSS/CCK)
  * burst 4     0.11 ms  snr   6.7 dB  cv  0.35  score 0.40  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 5     0.10 ms  snr   6.7 dB  cv  0.35  score 0.25  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 6     0.11 ms  snr   6.6 dB  cv  0.33  score 0.26  Wi-Fi 802.11b/g (DSSS/CCK)
  * burst 7     0.16 ms  snr   6.8 dB  cv  0.35  score 0.38  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 8     0.10 ms  snr   6.7 dB  cv  0.34  score 0.21  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 9     0.10 ms  snr   6.8 dB  cv  0.33  score 0.27  Wi-Fi 802.11b/g (DSSS/CCK)
  * burst 10    0.15 ms  snr   6.7 dB  cv  0.34  score 0.38  Wi-Fi 802.11b/g (DSSS/CCK)
  * burst 11    0.09 ms  snr   6.7 dB  cv  0.36  score 0.35  Wi-Fi 802.11b/g (DSSS/CCK)
  -> 12 bursts, 4 confident. missed (wanted Bluetooth LE 1M)

======================================================================
bluetooth_le1m_snr+10  --  2402.000 MHz, 79360 samples @ 8.0 MS/s
expected: Bluetooth LE 1M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================
    burst 0     0.27 ms  snr  10.9 dB  cv  0.22  score 0.13  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 1     0.27 ms  snr  10.9 dB  cv  0.22  score 0.07  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 2     0.27 ms  snr  10.9 dB  cv  0.21  score 0.07  Bluetooth LE 1M (GFSK)
    burst 3     0.27 ms  snr  10.9 dB  cv  0.21  score 0.12  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 4     0.27 ms  snr  10.9 dB  cv  0.21  score 0.03  Bluetooth LE 1M (GFSK)
    burst 5     0.27 ms  snr  10.9 dB  cv  0.22  score 0.09  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 6     0.27 ms  snr  10.9 dB  cv  0.21  score 0.06  SiK / MAVLink telemetry (2-FSK/GFSK)
    burst 7     0.27 ms  snr  11.0 dB  cv  0.22  score 0.06  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 8     0.27 ms  snr  10.9 dB  cv  0.21  score 0.08  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 9     0.27 ms  snr  10.9 dB  cv  0.21  score 0.05  SiK / MAVLink telemetry (2-FSK/GFSK)
    burst 10    0.27 ms  snr  10.9 dB  cv  0.22  score   -   (nothing scored)
    burst 11    0.27 ms  snr  10.9 dB  cv  0.22  score 0.10  Wi-Fi 802.11b/g (DSSS/CCK)
  -> 12 bursts, 0 confident. missed (wanted Bluetooth LE 1M)

======================================================================
bluetooth_le1m_snr+15  --  2402.000 MHz, 79360 samples @ 8.0 MS/s
expected: Bluetooth LE 1M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================
    burst 0     0.27 ms  snr  15.6 dB  cv  0.12  score 0.07  Bluetooth LE 1M (GFSK)
    burst 1     0.27 ms  snr  15.5 dB  cv  0.12  score 0.07  Bluetooth LE 1M (GFSK)
    burst 2     0.27 ms  snr  15.6 dB  cv  0.12  score 0.07  Bluetooth LE 1M (GFSK)
    burst 3     0.27 ms  snr  15.6 dB  cv  0.12  score 0.07  Bluetooth LE 1M (GFSK)
    burst 4     0.27 ms  snr  15.5 dB  cv  0.12  score 0.07  Bluetooth LE 1M (GFSK)
    burst 5     0.27 ms  snr  15.6 dB  cv  0.13  score 0.07  Bluetooth LE 1M (GFSK)
    burst 6     0.27 ms  snr  15.6 dB  cv  0.12  score 0.12  Bluetooth LE 2M (GFSK)
    burst 7     0.27 ms  snr  15.5 dB  cv  0.12  score 0.07  Bluetooth LE 1M (GFSK)
    burst 8     0.27 ms  snr  15.6 dB  cv  0.13  score 0.07  Bluetooth LE 1M (GFSK)
    burst 9     0.27 ms  snr  15.6 dB  cv  0.12  score 0.07  Bluetooth LE 1M (GFSK)
    burst 10    0.27 ms  snr  15.5 dB  cv  0.13  score 0.07  Bluetooth LE 1M (GFSK)
    burst 11    0.27 ms  snr  15.6 dB  cv  0.12  score 0.07  Bluetooth LE 1M (GFSK)
  -> 12 bursts, 0 confident. missed (wanted Bluetooth LE 1M)

  ======================================================================
bluetooth_le1m_snr-05  --  2402.000 MHz, 79360 samples @ 8.0 MS/s
expected: Bluetooth LE 1M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================
    burst 0     9.92 ms  snr   1.3 dB  cv  0.52  score 0.34  Wi-Fi 802.11b/g (DSSS/CCK)
  -> 1 bursts, 0 confident. missed (wanted Bluetooth LE 1M)

======================================================================
bluetooth_le1m_snr-10  --  2402.000 MHz, 79360 samples @ 8.0 MS/s
expected: Bluetooth LE 1M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================
    burst 0     9.92 ms  snr   0.7 dB  cv  0.52  score 0.27  Wi-Fi 802.11b/g (DSSS/CCK)
  -> 1 bursts, 0 confident. missed (wanted Bluetooth LE 1M)
```

- Clean sample was fine, SNR+00dB, SNR+05dB, SNR+10dB all failed - no idea why.

- Negative SNR samples also failed detection.

## Bandidth 99 estimation issues as SNR decreases

- Clean sample verbose output:

```
─── burst 0  t=0.510 ms  len=0.268 ms  SNR≈198.1 dB ───
  class          fsk2
  BW99 / RMS     1.222 MHz / 497.3 kHz   offset -19.88 kHz
  env CV / PAPR  0.000 / 0.0 dB   flatness 0.68  edge 19.0 dB
  symbol rate    1 MHz (line SNR 15381363.5x)
  FSK tones      2, deviation 284.2 kHz
  · symbol rate from squared-envelope
  · tone count via eye(w=1)
  candidates:
     99.1%  Bluetooth LE 1M (GFSK)
            spec: Bluetooth Core 5.4, Vol 6 Part B
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 1.222 MHz vs 800 kHz–1.4 MHz: 1.00
            · symbol rate 1 MHz vs 900 kHz–1.1 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 284.2 kHz: 0.95
     87.6%  Nordic/ANT-class 1 Mbps GFSK
            spec: ANT Message Protocol / nRF24 datasheet
            · modulation fsk2 vs fsk2: gate x1.00
            · BW99 1.222 MHz vs 800 kHz–1.4 MHz: 1.00
            · symbol rate 1 MHz vs 900 kHz–1.1 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 284.2 kHz: 0.49
     79.8%  Bluetooth Classic (GFSK, BR)
            spec: Bluetooth Core 5.4, Vol 6
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 1.222 MHz vs 700 kHz–1.3 MHz: 1.00
            · symbol rate 1 MHz vs 850 kHz–1.15 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 284.2 kHz: 0.30
```

- SNR+10dB output:
```
─── burst 0  t=0.510 ms  len=0.268 ms  SNR≈10.9 dB ───
  class          fsk2
  BW99 / RMS     7.215 MHz / 1.498 MHz   offset -6.381 kHz
  env CV / PAPR  0.216 / 4.7 dB   flatness 0.16  edge 12.7 dB
  symbol rate    1.07 MHz (line SNR 4.1x)
  FSK tones      2, deviation 226.9 kHz
  · symbol rate from fm-derivative
  · tone count via eye(w=4)
  NO CONFIDENT MATCH — closest entries, all weak:
     13.0%  Wi-Fi 802.11b/g (DSSS/CCK)
            spec: IEEE 802.11-2020 cl.16/17
            · modulation fsk2 vs dsss-psk/linear-shaped/const-env-phase: gate x0.55
            · BW99 7.215 MHz vs 14 MHz–24 MHz: 0.04
            · symbol rate 1.07 MHz vs 900 kHz–1.5 MHz: 1.00
            · burst 0.268 ms: 1.00
      7.5%  Bluetooth LE 1M (GFSK)
            spec: Bluetooth Core 5.4, Vol 6 Part B
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 7.215 MHz vs 800 kHz–1.4 MHz: 0.00
            · symbol rate 1.07 MHz vs 900 kHz–1.1 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 226.9 kHz: 1.00
      7.2%  Nordic/ANT-class 1 Mbps GFSK
            spec: ANT Message Protocol / nRF24 datasheet
            · modulation fsk2 vs fsk2: gate x1.00
            · BW99 7.215 MHz vs 800 kHz–1.4 MHz: 0.00
            · symbol rate 1.07 MHz vs 900 kHz–1.1 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 226.9 kHz: 0.82
```

- Synthetic noise was distorting bandwidth massively due to the PSD estimator used by Philip's code. 

- At +10 dB SNR, $P_s=1, P_n=0.1 \implies P_T = 1.1$ so the real BLE signal contains only $1/1.1=90.91%$ of all power, but BW99 goes off of 99% of total received power.

- To get 99% of total received power, we must capture $1-0.9091=8.09%$ of total power from the received noise.

- This corresponds to:

$$
\frac{0.99(1.1)-1}{0.1}=0.89=89\%\,\text{of all received AWGN.}
$$

- Which corresponds to $BW_{99} \approx 0.89(8\,\mathrm{MHz})=7.12\,\mathrm{MHz}$. This lines up with captures:

```
─── burst 0  t=0.510 ms  len=0.268 ms  SNR≈10.9 dB ───
  class          fsk2
  BW99 / RMS     7.215 MHz / 1.498 MHz   offset -6.381 kHz
  env CV / PAPR  0.216 / 4.7 dB   flatness 0.16  edge 12.7 dB
  symbol rate    1.07 MHz (line SNR 4.1x)
  FSK tones      2, deviation 226.9 kHz
  · symbol rate from fm-derivative
  · tone count via eye(w=4)
  NO CONFIDENT MATCH — closest entries, all weak:
     13.0%  Wi-Fi 802.11b/g (DSSS/CCK)
            spec: IEEE 802.11-2020 cl.16/17
            · modulation fsk2 vs dsss-psk/linear-shaped/const-env-phase: gate x0.55
            · BW99 7.215 MHz vs 14 MHz–24 MHz: 0.04
            · symbol rate 1.07 MHz vs 900 kHz–1.5 MHz: 1.00
            · burst 0.268 ms: 1.00
      7.5%  Bluetooth LE 1M (GFSK)
            spec: Bluetooth Core 5.4, Vol 6 Part B
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 7.215 MHz vs 800 kHz–1.4 MHz: 0.00
            · symbol rate 1.07 MHz vs 900 kHz–1.1 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 226.9 kHz: 1.00
      7.2%  Nordic/ANT-class 1 Mbps GFSK
            spec: ANT Message Protocol / nRF24 datasheet
            · modulation fsk2 vs fsk2: gate x1.00
            · BW99 7.215 MHz vs 800 kHz–1.4 MHz: 0.00
            · symbol rate 1.07 MHz vs 900 kHz–1.1 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 226.9 kHz: 0.82

─── burst 1  t=1.006 ms  len=0.268 ms  SNR≈10.9 dB ───
  class          fsk2
  BW99 / RMS     7.211 MHz / 1.485 MHz   offset -5.272 kHz
  env CV / PAPR  0.219 / 4.8 dB   flatness 0.16  edge 12.9 dB
  symbol rate    863.3 kHz (line SNR 3.8x)
  FSK tones      2, deviation 270.5 kHz
  · symbol rate from fm-derivative
  · tone count via eye(w=5)
  NO CONFIDENT MATCH — closest entries, all weak:
      6.7%  Wi-Fi 802.11b/g (DSSS/CCK)
            spec: IEEE 802.11-2020 cl.16/17
            · modulation fsk2 vs dsss-psk/linear-shaped/const-env-phase: gate x0.55
            · BW99 7.211 MHz vs 14 MHz–24 MHz: 0.04
            · burst 0.268 ms: 1.00
      3.2%  Bluetooth LE 1M (GFSK)
            spec: Bluetooth Core 5.4, Vol 6 Part B
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 7.211 MHz vs 800 kHz–1.4 MHz: 0.00
            · burst 0.268 ms: 1.00
            · FSK deviation 270.5 kHz: 1.00
      2.7%  Nordic/ANT-class 1 Mbps GFSK
            spec: ANT Message Protocol / nRF24 datasheet
            · modulation fsk2 vs fsk2: gate x1.00
            · BW99 7.211 MHz vs 800 kHz–1.4 MHz: 0.00
            · burst 0.268 ms: 1.00
            · FSK deviation 270.5 kHz: 0.56

─── burst 2  t=1.502 ms  len=0.268 ms  SNR≈10.9 dB ───
  class          fsk2
  BW99 / RMS     7.031 MHz / 1.427 MHz   offset -48.21 kHz
  env CV / PAPR  0.210 / 4.5 dB   flatness 0.15  edge 13.6 dB
  symbol rate    1 MHz (line SNR 5.0x)
  FSK tones      2, deviation 262.1 kHz
  · symbol rate from fm-sign-transitions
  · tone count via blanket(w=4)
  NO CONFIDENT MATCH — closest entries, all weak:
      7.5%  Bluetooth LE 1M (GFSK)
            spec: Bluetooth Core 5.4, Vol 6 Part B
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 7.031 MHz vs 800 kHz–1.4 MHz: 0.00
            · symbol rate 1 MHz vs 900 kHz–1.1 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 262.1 kHz: 1.00
      6.8%  Nordic/ANT-class 1 Mbps GFSK
            spec: ANT Message Protocol / nRF24 datasheet
            · modulation fsk2 vs fsk2: gate x1.00
            · BW99 7.031 MHz vs 800 kHz–1.4 MHz: 0.00
            · symbol rate 1 MHz vs 900 kHz–1.1 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 262.1 kHz: 0.61
      6.4%  Bluetooth Classic (GFSK, BR)
            spec: Bluetooth Core 5.4, Vol 6
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 7.031 MHz vs 700 kHz–1.3 MHz: 0.00
            · symbol rate 1 MHz vs 850 kHz–1.15 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 262.1 kHz: 0.42
```

- Similarly for +15dB:

$$
P_N = 10^{-15/10}=0.031625P_S
$$

- Signal accounts for:

$$
\frac{1}{1.031625}=96.93\%\,\text{ of the total power.}
$$

- To reach 99%:

$$
\frac{0.99(1.031625)-1}{0.031625}\approx 0.674
$$

- Which corresponds to $BW_{99} \approx 0.674(8\,\mathrm{MHz})=5.39\,\mathrm{MHz}$. This also lined up with results.

```
─── burst 0  t=0.510 ms  len=0.268 ms  SNR≈15.6 dB ───
  class          fsk2
  BW99 / RMS     5.394 MHz / 955.5 kHz   offset -68.61 kHz
  env CV / PAPR  0.124 / 2.7 dB   flatness 0.08  edge 19.0 dB
  symbol rate    1 MHz (line SNR 5.6x)
  FSK tones      2, deviation 292.4 kHz
  repetition     period 40 samp (rho 0.66), CFO -83089 Hz mod 200 kHz
  · repeating structure at 40 samples (rho 0.66); CFO -83089 Hz modulo 200000 Hz
  · symbol rate from fm-sign-transitions
  · tone count via eye(w=1)
  NO CONFIDENT MATCH — closest entries, all weak:
      7.4%  Bluetooth LE 1M (GFSK)
            spec: Bluetooth Core 5.4, Vol 6 Part B
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 5.394 MHz vs 800 kHz–1.4 MHz: 0.00
            · symbol rate 1 MHz vs 900 kHz–1.1 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 292.4 kHz: 0.91
      6.5%  Nordic/ANT-class 1 Mbps GFSK
            spec: ANT Message Protocol / nRF24 datasheet
            · modulation fsk2 vs fsk2: gate x1.00
            · BW99 5.394 MHz vs 800 kHz–1.4 MHz: 0.00
            · symbol rate 1 MHz vs 900 kHz–1.1 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 292.4 kHz: 0.45
      5.8%  Bluetooth Classic (GFSK, BR)
            spec: Bluetooth Core 5.4, Vol 6
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 5.394 MHz vs 700 kHz–1.3 MHz: 0.00
            · symbol rate 1 MHz vs 850 kHz–1.15 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 292.4 kHz: 0.26

─── burst 1  t=1.006 ms  len=0.268 ms  SNR≈15.5 dB ───
  class          fsk2
  BW99 / RMS     5.504 MHz / 963.6 kHz   offset 48.46 kHz
  env CV / PAPR  0.123 / 3.1 dB   flatness 0.08  edge 18.8 dB
  symbol rate    1 MHz (line SNR 7.2x)
  FSK tones      2, deviation 334.3 kHz
  · symbol rate from fm-sign-transitions
  · tone count via eye(w=2)
  NO CONFIDENT MATCH — closest entries, all weak:
      7.0%  Bluetooth LE 1M (GFSK)
            spec: Bluetooth Core 5.4, Vol 6 Part B
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 5.504 MHz vs 800 kHz–1.4 MHz: 0.00
            · symbol rate 1 MHz vs 900 kHz–1.1 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 334.3 kHz: 0.72
      5.8%  Nordic/ANT-class 1 Mbps GFSK
            spec: ANT Message Protocol / nRF24 datasheet
            · modulation fsk2 vs fsk2: gate x1.00
            · BW99 5.504 MHz vs 800 kHz–1.4 MHz: 0.00
            · symbol rate 1 MHz vs 900 kHz–1.1 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 334.3 kHz: 0.26
      4.9%  Bluetooth LE 2M (GFSK)
            spec: Bluetooth Core 5.4
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 5.504 MHz vs 1.6 MHz–2.6 MHz: 0.00
            · symbol rate 1 MHz vs 1.8 MHz–2.2 MHz: 0.29
            · burst 0.268 ms: 0.96
            · FSK deviation 334.3 kHz: 0.57

─── burst 2  t=1.502 ms  len=0.268 ms  SNR≈15.6 dB ───
  class          fsk2
  BW99 / RMS     5.605 MHz / 972.6 kHz   offset -42.81 kHz
  env CV / PAPR  0.124 / 2.9 dB   flatness 0.08  edge 18.9 dB
  symbol rate    1 MHz (line SNR 6.5x)
  FSK tones      2, deviation 289.6 kHz
  · symbol rate from fm-sign-transitions
  · tone count via eye(w=2)
  NO CONFIDENT MATCH — closest entries, all weak:
      7.4%  Bluetooth LE 1M (GFSK)
            spec: Bluetooth Core 5.4, Vol 6 Part B
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 5.605 MHz vs 800 kHz–1.4 MHz: 0.00
            · symbol rate 1 MHz vs 900 kHz–1.1 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 289.6 kHz: 0.93
      6.5%  Nordic/ANT-class 1 Mbps GFSK
            spec: ANT Message Protocol / nRF24 datasheet
            · modulation fsk2 vs fsk2: gate x1.00
            · BW99 5.605 MHz vs 800 kHz–1.4 MHz: 0.00
            · symbol rate 1 MHz vs 900 kHz–1.1 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 289.6 kHz: 0.47
      5.9%  Bluetooth Classic (GFSK, BR)
            spec: Bluetooth Core 5.4, Vol 6
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 5.605 MHz vs 700 kHz–1.3 MHz: 0.00
            · symbol rate 1 MHz vs 850 kHz–1.15 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 289.6 kHz: 0.27
```

- This only stops being an issue for SNR+20dB where $P_N = 10^{-20/10} = 0.01P_S$, so signal already takes up $1/1.01=99.01\%$ of total signal and fulfills BW99 requirements truthfully.

- BW99 is somewhat broken!

    - We also have a sample rate dependency. We measured 8MHz sampled bandwidth due to 8 MS/s sample rate. At other sample rates this would affect the estimated BW99:
        
        - 4MS/s: $BW_{99} \approx 0.89(4\,\mathrm{MHz}) = 3.56\,\mathrm{MHz}$
        - 12MS/s: $BW_{99} \approx 0.89(12\,\mathrm{MHz}) = 10.68\,\mathrm{MHz}$
        - 20MS/s: $BW_{99} \approx 0.89(20\,\mathrm{MHz}) = 17.8\,\mathrm{MHz}$

    - So the detector reports wildly different occupied bandwidths based on sample rate.

- Potential upgrade: $P_\text{signal​}(f)=\mathrm{max}(P_\text{measured​}(f)−P^N​(f),\,0)$

- Experiment: Same BLE signal generated at different sample rates.

    - Clean BW99 should stay independent of $F_s$.

    - Noisy (+10dB SNR) BW99 should be around $0.89F_{s}$

- `gen_bluetooth_fs_sweep.m` created to generate sweep through $F_s \in [4, 8, 12, 16, 20]\,\text{MHz}$

```
======================================================================
bluetooth_le1m_fs20m_clean  --  2402.000 MHz, 198400 samples @ 20.0 MS/s
expected: Bluetooth LE 1M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================

─── burst 0  t=0.510 ms  len=0.268 ms  SNR≈198.1 dB ───
  class          fsk2
  BW99 / RMS     1.218 MHz / 498.7 kHz   offset 356.3 Hz
  env CV / PAPR  0.000 / 0.0 dB   flatness 0.69  edge 20.3 dB
  symbol rate    1.001 MHz (line SNR 1393929.0x)
  FSK tones      2, deviation 277.9 kHz
  · symbol rate from squared-envelope
  · tone count via blanket(w=10)
  candidates:
     99.7%  Bluetooth LE 1M (GFSK)
            spec: Bluetooth Core 5.4, Vol 6 Part B
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 1.218 MHz vs 800 kHz–1.4 MHz: 1.00
            · symbol rate 1.001 MHz vs 900 kHz–1.1 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 277.9 kHz: 0.98
     88.6%  Nordic/ANT-class 1 Mbps GFSK
            spec: ANT Message Protocol / nRF24 datasheet
            · modulation fsk2 vs fsk2: gate x1.00
            · BW99 1.218 MHz vs 800 kHz–1.4 MHz: 1.00
            · symbol rate 1.001 MHz vs 900 kHz–1.1 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 277.9 kHz: 0.53
     81.4%  Bluetooth Classic (GFSK, BR)
            spec: Bluetooth Core 5.4, Vol 6
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 1.218 MHz vs 700 kHz–1.3 MHz: 1.00
            · symbol rate 1.001 MHz vs 850 kHz–1.15 MHz: 1.00
            · burst 0.268 ms: 1.00
            · FSK deviation 277.9 kHz: 0.33

======================================================================
bluetooth_le1m_fs20m_snr+10  --  2402.000 MHz, 198400 samples @ 20.0 MS/s
expected: Bluetooth LE 1M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================

─── burst 0  t=0.510 ms  len=0.267 ms  SNR≈10.7 dB ───
  class          const-env-phase
  BW99 / RMS     17.68 MHz / 3.487 MHz   offset 25.94 kHz
  env CV / PAPR  0.215 / 4.5 dB   flatness 0.11  edge 13.2 dB
  symbol rate    3.193 MHz (line SNR 4.9x)
  FSK tones      1, deviation 0 Hz
  · symbol rate from fm-derivative
  · tone count via blanket(w=3)
  candidates:
     47.9%  Wi-Fi 802.11b/g (DSSS/CCK)
            spec: IEEE 802.11-2020 cl.16/17
            · modulation const-env-phase vs dsss-psk/linear-shaped/const-env-phase: gate x1.00
            · BW99 17.68 MHz vs 14 MHz–24 MHz: 1.00
            · symbol rate 3.193 MHz vs 900 kHz–1.5 MHz: 0.09
            · burst 0.267 ms: 1.00
      3.4%  Bluetooth LE 2M (GFSK)
            spec: Bluetooth Core 5.4
            · modulation const-env-phase vs fsk2/const-env-phase: gate x1.00
            · BW99 17.68 MHz vs 1.6 MHz–2.6 MHz: 0.00
            · symbol rate 3.193 MHz vs 1.8 MHz–2.2 MHz: 0.55
            · burst 0.267 ms: 0.96
```

- Note that `--verbose` output on entire sweep was huge, I could only see 16MHz Fs with +10dB SNR and the 20MHz Fs results. Regardless, we are able to find all the results we need by only comparing a 20MHz clean and +10 dB analysis. 

- Estimated BLE 1M with 99.7% confidence on clean sample, but failed on +10dB SNR sample with occupied bandwidth estimate matching almost exactly our previously calculated value of $17.8\,\text{MHz}$.

    - Therefore BW99 at moderate SNR is tracking observation bandwidth / noise instead of actual occupied bandwidth!

# Onto Zigbee with `gen_zigbee.m`

- Same story as bluetooth. Zigbee is generated using `lrwpanOQPSKConfig` from $\mathrm{MATLAB}$. We generate 12 bursts from SNR $\in [-10, -5, 0, 5, 10, 15, 20, 30, \mathrm{inf}]\,\text{dB}$

- Initial run:

```
(.venv) petervertsonis@Peters-MacBook-Pro thesis % python validation/experiments/run_sweep_id.py \              
    --dir generated \
    --only $(find -H captures/generated -maxdepth 1 \
        -name 'zigbee_oqpsk*.npy' \
        -exec basename {} .npy \;)

======================================================================
zigbee_oqpsk_clean  --  2405.000 MHz, 159544 samples @ 4.0 MS/s
expected: Zigbee / 802.15.4 O-QPSK DSSS  (O-QPSK DSSS)
antenna: None  gain: None dB
======================================================================
  * burst 0     2.02 ms  snr 198.1 dB  cv  0.00  score 0.55  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 1     2.02 ms  snr 198.1 dB  cv  0.00  score 0.55  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 2     2.02 ms  snr 198.1 dB  cv  0.00  score 0.55  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 3     2.02 ms  snr 198.1 dB  cv  0.00  score 0.55  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 4     2.02 ms  snr 198.1 dB  cv  0.00  score 0.55  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 5     2.02 ms  snr 198.1 dB  cv  0.00  score 0.55  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 6     2.02 ms  snr 198.1 dB  cv  0.00  score 0.55  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 7     2.02 ms  snr 198.1 dB  cv  0.00  score 0.55  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 8     2.02 ms  snr 198.1 dB  cv  0.00  score 0.55  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 9     2.02 ms  snr 198.1 dB  cv  0.00  score 0.55  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 10    2.02 ms  snr 198.1 dB  cv  0.00  score 0.55  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 11    2.02 ms  snr 198.1 dB  cv  0.00  score 0.55  Zigbee / 802.15.4 O-QPSK DSSS
  -> 12 bursts, 12 confident. CORRECT

======================================================================
zigbee_oqpsk_snr+00  --  2405.000 MHz, 159544 samples @ 4.0 MS/s
expected: Zigbee / 802.15.4 O-QPSK DSSS  (O-QPSK DSSS)
antenna: None  gain: None dB
======================================================================
    burst 0    39.89 ms  snr   2.7 dB  cv  0.51  score 0.08  LTE / 5G NR downlink (OFDM, 15 kHz SCS)
  -> 1 bursts, 0 confident. missed (wanted Zigbee / 802.15.4 O-QPSK DSSS)

======================================================================
zigbee_oqpsk_snr+05  --  2405.000 MHz, 159544 samples @ 4.0 MS/s
expected: Zigbee / 802.15.4 O-QPSK DSSS  (O-QPSK DSSS)
antenna: None  gain: None dB
======================================================================
  * burst 0     0.14 ms  snr   6.8 dB  cv  0.34  score 0.70  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 1     0.13 ms  snr   6.7 dB  cv  0.33  score 0.77  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 2     0.15 ms  snr   6.7 dB  cv  0.36  score 0.71  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 3     0.20 ms  snr   6.8 dB  cv  0.35  score 0.74  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 4     0.16 ms  snr   6.6 dB  cv  0.34  score 0.71  Zigbee / 802.15.4 O-QPSK DSSS
    burst 5     0.14 ms  snr   6.7 dB  cv  0.35  score 0.10  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 6     0.18 ms  snr   6.9 dB  cv  0.34  score 0.80  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 7     0.15 ms  snr   6.8 dB  cv  0.34  score 0.72  Zigbee / 802.15.4 O-QPSK DSSS
    burst 8     0.20 ms  snr   6.8 dB  cv  0.32  score 0.11  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 9     0.21 ms  snr   6.9 dB  cv  0.34  score 0.76  Zigbee / 802.15.4 O-QPSK DSSS
    burst 10    0.17 ms  snr   7.0 dB  cv  0.35  score 0.11  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 11    0.13 ms  snr   6.6 dB  cv  0.35  score 0.67  Zigbee / 802.15.4 O-QPSK DSSS
  -> 12 bursts, 9 confident. CORRECT

======================================================================
zigbee_oqpsk_snr+10  --  2405.000 MHz, 159544 samples @ 4.0 MS/s
expected: Zigbee / 802.15.4 O-QPSK DSSS  (O-QPSK DSSS)
antenna: None  gain: None dB
======================================================================
  * burst 0     2.02 ms  snr  10.8 dB  cv  0.21  score 0.46  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 1     2.02 ms  snr  10.8 dB  cv  0.22  score 0.46  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 2     2.02 ms  snr  10.8 dB  cv  0.21  score 0.46  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 3     2.02 ms  snr  10.8 dB  cv  0.21  score 0.46  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 4     2.02 ms  snr  10.8 dB  cv  0.21  score 0.46  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 5     2.02 ms  snr  10.8 dB  cv  0.21  score 0.46  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 6     2.02 ms  snr  10.8 dB  cv  0.21  score 0.46  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 7     2.02 ms  snr  10.8 dB  cv  0.22  score 0.46  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 8     2.02 ms  snr  10.8 dB  cv  0.22  score 0.46  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 9     2.02 ms  snr  10.9 dB  cv  0.21  score 0.46  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 10    2.02 ms  snr  10.8 dB  cv  0.22  score 0.46  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 11    2.02 ms  snr  10.8 dB  cv  0.21  score 0.46  Zigbee / 802.15.4 O-QPSK DSSS
  -> 12 bursts, 12 confident. CORRECT

======================================================================
zigbee_oqpsk_snr+15  --  2405.000 MHz, 159544 samples @ 4.0 MS/s
expected: Zigbee / 802.15.4 O-QPSK DSSS  (O-QPSK DSSS)
antenna: None  gain: None dB
======================================================================
  * burst 0     2.02 ms  snr  15.5 dB  cv  0.12  score 0.48  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 1     2.02 ms  snr  15.5 dB  cv  0.13  score 0.48  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 2     2.02 ms  snr  15.5 dB  cv  0.12  score 0.48  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 3     2.02 ms  snr  15.5 dB  cv  0.12  score 0.48  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 4     2.02 ms  snr  15.5 dB  cv  0.12  score 0.48  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 5     2.02 ms  snr  15.6 dB  cv  0.12  score 0.48  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 6     2.02 ms  snr  15.5 dB  cv  0.12  score 0.48  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 7     2.02 ms  snr  15.6 dB  cv  0.12  score 0.48  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 8     2.02 ms  snr  15.5 dB  cv  0.12  score 0.48  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 9     2.02 ms  snr  15.5 dB  cv  0.12  score 0.48  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 10    2.02 ms  snr  15.5 dB  cv  0.12  score 0.48  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 11    2.02 ms  snr  15.5 dB  cv  0.12  score 0.49  Zigbee / 802.15.4 O-QPSK DSSS
  -> 12 bursts, 12 confident. CORRECT

======================================================================
zigbee_oqpsk_snr+20  --  2405.000 MHz, 159544 samples @ 4.0 MS/s
expected: Zigbee / 802.15.4 O-QPSK DSSS  (O-QPSK DSSS)
antenna: None  gain: None dB
======================================================================
  * burst 0     2.02 ms  snr  20.6 dB  cv  0.07  score 0.50  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 1     2.02 ms  snr  20.6 dB  cv  0.07  score 0.50  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 2     2.02 ms  snr  20.6 dB  cv  0.07  score 0.51  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 3     2.02 ms  snr  20.6 dB  cv  0.07  score 0.51  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 4     2.02 ms  snr  20.6 dB  cv  0.07  score 0.50  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 5     2.02 ms  snr  20.6 dB  cv  0.07  score 0.50  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 6     2.02 ms  snr  20.5 dB  cv  0.07  score 0.50  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 7     2.02 ms  snr  20.6 dB  cv  0.07  score 0.51  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 8     2.02 ms  snr  20.6 dB  cv  0.07  score 0.50  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 9     2.02 ms  snr  20.6 dB  cv  0.07  score 0.50  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 10    2.02 ms  snr  20.5 dB  cv  0.07  score 0.50  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 11    2.02 ms  snr  20.6 dB  cv  0.07  score 0.50  Zigbee / 802.15.4 O-QPSK DSSS
  -> 12 bursts, 12 confident. CORRECT

======================================================================
zigbee_oqpsk_snr+30  --  2405.000 MHz, 159544 samples @ 4.0 MS/s
expected: Zigbee / 802.15.4 O-QPSK DSSS  (O-QPSK DSSS)
antenna: None  gain: None dB
======================================================================
  * burst 0     2.02 ms  snr  30.4 dB  cv  0.02  score 0.54  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 1     2.02 ms  snr  30.4 dB  cv  0.02  score 0.54  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 2     2.02 ms  snr  30.4 dB  cv  0.02  score 0.55  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 3     2.02 ms  snr  30.4 dB  cv  0.02  score 0.54  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 4     2.02 ms  snr  30.4 dB  cv  0.02  score 0.54  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 5     2.02 ms  snr  30.4 dB  cv  0.02  score 0.54  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 6     2.02 ms  snr  30.4 dB  cv  0.02  score 0.54  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 7     2.02 ms  snr  30.4 dB  cv  0.02  score 0.54  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 8     2.02 ms  snr  30.4 dB  cv  0.02  score 0.54  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 9     2.02 ms  snr  30.4 dB  cv  0.02  score 0.53  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 10    2.02 ms  snr  30.4 dB  cv  0.02  score 0.55  Zigbee / 802.15.4 O-QPSK DSSS
  * burst 11    2.02 ms  snr  30.4 dB  cv  0.02  score 0.54  Zigbee / 802.15.4 O-QPSK DSSS
  -> 12 bursts, 12 confident. CORRECT

======================================================================
zigbee_oqpsk_snr-05  --  2405.000 MHz, 159544 samples @ 4.0 MS/s
expected: Zigbee / 802.15.4 O-QPSK DSSS  (O-QPSK DSSS)
antenna: None  gain: None dB
======================================================================
    burst 0    39.89 ms  snr   1.2 dB  cv  0.52  score 0.20  LTE / 5G NR downlink (OFDM, 15 kHz SCS)
  -> 1 bursts, 0 confident. missed (wanted Zigbee / 802.15.4 O-QPSK DSSS)

======================================================================
zigbee_oqpsk_snr-10  --  2405.000 MHz, 159544 samples @ 4.0 MS/s
expected: Zigbee / 802.15.4 O-QPSK DSSS  (O-QPSK DSSS)
antenna: None  gain: None dB
======================================================================
    burst 0    39.89 ms  snr   0.8 dB  cv  0.52  score 0.20  LTE / 5G NR downlink (OFDM, 15 kHz SCS)
  -> 1 bursts, 0 confident. missed (wanted Zigbee / 802.15.4 O-QPSK DSSS)

======================================================================
SUMMARY
======================================================================
band        bursts  conf  result
zigbee_oqpsk_clean      12    12  CORRECT
zigbee_oqpsk_snr+00       1     0  missed (wanted Zigbee / 802.15.4 O-QPSK DSSS)
zigbee_oqpsk_snr+05      12     9  CORRECT
zigbee_oqpsk_snr+10      12    12  CORRECT
zigbee_oqpsk_snr+15      12    12  CORRECT
zigbee_oqpsk_snr+20      12    12  CORRECT
zigbee_oqpsk_snr+30      12    12  CORRECT
zigbee_oqpsk_snr-05       1     0  missed (wanted Zigbee / 802.15.4 O-QPSK DSSS)
zigbee_oqpsk_snr-10       1     0  missed (wanted Zigbee / 802.15.4 O-QPSK DSSS)
```

- Mainly burst detection issues. Once SNR gets around and below 0dB, bursts become longer and longer -> we're no longer feeding the detector actual Zigbee packets, but instead, a lot of noise.

- To understand what's happening consider 0dB case where $P_N = P_S$, so total power when the detector is actually receiving a packet it sees power $P_\text{ON} = P_S + P_N = 2P_N$, which relative to the noise floor is only:

$$
10\log_{10}\left(\frac{P_S+P_N}{P_N}\right)=10\log_{10}(2)=3.01\,\text{dB}
$$

- But, the burst detection logic requires $+8\,\text{dB}$ power relative to noise floor to 'start' a burst. Generally, ON/OFF energy contrast is:

$$
\Delta P = 10\log_{10}\left(1+10^{\text{SNR}/10}\right)
$$

- Which can be solved to find the boundary point for consistent burst detection:

$$
10\log_{10}\left(1+10^{\text{SNR}/10}\right) = 8 \implies \text{SNR} \approx 7.25\,\text{dB}
$$

- Which explains why our +5dB sample recorded only 9 confident Zigbee classifications.

- The problem here is that segmentation never gives the lower SNR samples a chance to actually analyse a Zigbee packet. Once SNR gets low enough, the burst smudges more and more which makes it much more difficult for reliable classifications.

# Back to Bluetooth - Bluetooth LE 2M with `gen_bluetooth_le2m.m`

- Initial run:

```
(.venv) petervertsonis@Peters-MacBook-Pro thesis % python validation/experiments/run_sweep_id.py \
    --dir generated \
    --only $(find -H captures/generated -maxdepth 1 \
        -name 'bluetooth_le2m*.npy' \
        -exec basename {} .npy \;)

======================================================================
bluetooth_le2m_clean  --  2402.000 MHz, 56320 samples @ 8.0 MS/s
expected: Bluetooth LE 2M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================
  * burst 0     0.14 ms  snr 198.1 dB  cv  0.00  score 0.99  Bluetooth LE 2M (GFSK)
  * burst 1     0.14 ms  snr 198.1 dB  cv  0.00  score 0.96  Bluetooth LE 2M (GFSK)
  * burst 2     0.14 ms  snr 198.1 dB  cv  0.00  score 1.00  Bluetooth LE 2M (GFSK)
  * burst 3     0.14 ms  snr 198.1 dB  cv  0.00  score 0.96  Bluetooth LE 2M (GFSK)
  * burst 4     0.14 ms  snr 198.1 dB  cv  0.00  score 0.96  Bluetooth LE 2M (GFSK)
  * burst 5     0.14 ms  snr 198.1 dB  cv  0.00  score 0.96  Bluetooth LE 2M (GFSK)
  * burst 6     0.14 ms  snr 198.1 dB  cv  0.00  score 1.00  Bluetooth LE 2M (GFSK)
  * burst 7     0.14 ms  snr 198.1 dB  cv  0.00  score 0.96  Bluetooth LE 2M (GFSK)
  * burst 8     0.14 ms  snr 198.1 dB  cv  0.00  score 0.96  Bluetooth LE 2M (GFSK)
  * burst 9     0.14 ms  snr 198.1 dB  cv  0.00  score 0.96  Bluetooth LE 2M (GFSK)
  * burst 10    0.14 ms  snr 198.1 dB  cv  0.00  score 1.00  Bluetooth LE 2M (GFSK)
  * burst 11    0.14 ms  snr 198.1 dB  cv  0.00  score 0.96  Bluetooth LE 2M (GFSK)
  -> 12 bursts, 12 confident. CORRECT

======================================================================
bluetooth_le2m_snr+00  --  2402.000 MHz, 56320 samples @ 8.0 MS/s
expected: Bluetooth LE 2M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================
    burst 0     7.04 ms  snr   2.1 dB  cv  0.53  score 0.08  LTE / 5G NR downlink (OFDM, 15 kHz SCS)
  -> 1 bursts, 0 confident. missed (wanted Bluetooth LE 2M)

======================================================================
bluetooth_le2m_snr+05  --  2402.000 MHz, 56320 samples @ 8.0 MS/s
expected: Bluetooth LE 2M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================
    burst 0     0.14 ms  snr   7.0 dB  cv  0.34  score 0.17  5G NR (OFDM, 30 kHz SCS)
    burst 1     0.14 ms  snr   6.9 dB  cv  0.34  score 0.23  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 2     0.09 ms  snr   6.9 dB  cv  0.35  score 0.27  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 3     0.09 ms  snr   6.8 dB  cv  0.35  score 0.27  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 4     0.08 ms  snr   6.9 dB  cv  0.35  score 0.26  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 5     0.11 ms  snr   6.9 dB  cv  0.34  score 0.25  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 6     0.13 ms  snr   6.7 dB  cv  0.36  score 0.26  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 7     0.11 ms  snr   6.8 dB  cv  0.36  score 0.16  5G NR (OFDM, 30 kHz SCS)
    burst 8     0.14 ms  snr   6.9 dB  cv  0.37  score 0.25  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 9     0.14 ms  snr   6.8 dB  cv  0.35  score 0.25  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 10    0.08 ms  snr   6.9 dB  cv  0.35  score 0.24  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 11    0.14 ms  snr   6.7 dB  cv  0.35  score 0.29  Wi-Fi 802.11b/g (DSSS/CCK)
  -> 12 bursts, 0 confident. missed (wanted Bluetooth LE 2M)

======================================================================
bluetooth_le2m_snr+10  --  2402.000 MHz, 56320 samples @ 8.0 MS/s
expected: Bluetooth LE 2M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================
    burst 0     0.14 ms  snr  10.9 dB  cv  0.21  score 0.07  Bluetooth LE 2M (GFSK)
    burst 1     0.14 ms  snr  10.9 dB  cv  0.21  score 0.09  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 2     0.14 ms  snr  11.0 dB  cv  0.21  score 0.08  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 3     0.14 ms  snr  11.0 dB  cv  0.22  score 0.10  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 4     0.14 ms  snr  11.0 dB  cv  0.22  score 0.07  Bluetooth LE 2M (GFSK)
    burst 5     0.14 ms  snr  11.0 dB  cv  0.21  score 0.07  Bluetooth LE 2M (GFSK)
    burst 6     0.14 ms  snr  11.0 dB  cv  0.22  score 0.11  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 7     0.14 ms  snr  10.9 dB  cv  0.21  score 0.09  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 8     0.14 ms  snr  10.9 dB  cv  0.22  score 0.09  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 9     0.14 ms  snr  11.0 dB  cv  0.22  score 0.10  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 10    0.14 ms  snr  11.0 dB  cv  0.22  score 0.09  Wi-Fi 802.11b/g (DSSS/CCK)
    burst 11    0.14 ms  snr  10.9 dB  cv  0.21  score 0.10  Wi-Fi 802.11b/g (DSSS/CCK)
  -> 12 bursts, 0 confident. missed (wanted Bluetooth LE 2M)

======================================================================
bluetooth_le2m_snr+15  --  2402.000 MHz, 56320 samples @ 8.0 MS/s
expected: Bluetooth LE 2M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================
    burst 0     0.14 ms  snr  15.7 dB  cv  0.13  score 0.07  Bluetooth LE 2M (GFSK)
    burst 1     0.14 ms  snr  15.7 dB  cv  0.13  score 0.07  Bluetooth LE 2M (GFSK)
    burst 2     0.14 ms  snr  15.7 dB  cv  0.12  score 0.07  Bluetooth LE 2M (GFSK)
    burst 3     0.14 ms  snr  15.7 dB  cv  0.12  score 0.07  Bluetooth LE 2M (GFSK)
    burst 4     0.14 ms  snr  15.7 dB  cv  0.12  score 0.07  Bluetooth LE 2M (GFSK)
    burst 5     0.14 ms  snr  15.7 dB  cv  0.13  score 0.07  Bluetooth LE 2M (GFSK)
    burst 6     0.14 ms  snr  15.7 dB  cv  0.12  score 0.07  Bluetooth LE 2M (GFSK)
    burst 7     0.14 ms  snr  15.7 dB  cv  0.12  score 0.07  Bluetooth LE 2M (GFSK)
    burst 8     0.14 ms  snr  15.7 dB  cv  0.13  score 0.07  Bluetooth LE 2M (GFSK)
    burst 9     0.14 ms  snr  15.7 dB  cv  0.13  score 0.07  Bluetooth LE 2M (GFSK)
    burst 10    0.14 ms  snr  15.7 dB  cv  0.12  score 0.07  Bluetooth LE 2M (GFSK)
    burst 11    0.14 ms  snr  15.7 dB  cv  0.12  score 0.07  Bluetooth LE 2M (GFSK)
  -> 12 bursts, 0 confident. missed (wanted Bluetooth LE 2M)

======================================================================
bluetooth_le2m_snr+20  --  2402.000 MHz, 56320 samples @ 8.0 MS/s
expected: Bluetooth LE 2M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================
  * burst 0     0.14 ms  snr  20.6 dB  cv  0.07  score 0.74  Bluetooth LE 2M (GFSK)
  * burst 1     0.14 ms  snr  20.6 dB  cv  0.07  score 0.72  Bluetooth LE 2M (GFSK)
  * burst 2     0.14 ms  snr  20.5 dB  cv  0.07  score 0.74  Bluetooth LE 2M (GFSK)
  * burst 3     0.14 ms  snr  20.6 dB  cv  0.07  score 0.71  Bluetooth LE 2M (GFSK)
  * burst 4     0.14 ms  snr  20.6 dB  cv  0.07  score 0.72  Bluetooth LE 2M (GFSK)
  * burst 5     0.14 ms  snr  20.6 dB  cv  0.07  score 0.76  Bluetooth LE 2M (GFSK)
  * burst 6     0.14 ms  snr  20.6 dB  cv  0.07  score 0.77  Bluetooth LE 2M (GFSK)
  * burst 7     0.14 ms  snr  20.6 dB  cv  0.07  score 0.74  Bluetooth LE 2M (GFSK)
  * burst 8     0.14 ms  snr  20.6 dB  cv  0.07  score 0.81  Bluetooth LE 2M (GFSK)
  * burst 9     0.14 ms  snr  20.6 dB  cv  0.07  score 0.78  Bluetooth LE 2M (GFSK)
  * burst 10    0.14 ms  snr  20.6 dB  cv  0.07  score 0.71  Bluetooth LE 2M (GFSK)
  * burst 11    0.14 ms  snr  20.6 dB  cv  0.07  score 0.79  Bluetooth LE 2M (GFSK)
  -> 12 bursts, 12 confident. CORRECT

======================================================================
bluetooth_le2m_snr+30  --  2402.000 MHz, 56320 samples @ 8.0 MS/s
expected: Bluetooth LE 2M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================
  * burst 0     0.14 ms  snr  30.5 dB  cv  0.02  score 1.00  Bluetooth LE 2M (GFSK)
  * burst 1     0.14 ms  snr  30.5 dB  cv  0.02  score 0.99  Bluetooth LE 2M (GFSK)
  * burst 2     0.14 ms  snr  30.5 dB  cv  0.02  score 1.00  Bluetooth LE 2M (GFSK)
  * burst 3     0.14 ms  snr  30.5 dB  cv  0.02  score 1.00  Bluetooth LE 2M (GFSK)
  * burst 4     0.14 ms  snr  30.5 dB  cv  0.02  score 1.00  Bluetooth LE 2M (GFSK)
  * burst 5     0.14 ms  snr  30.5 dB  cv  0.02  score 1.00  Bluetooth LE 2M (GFSK)
  * burst 6     0.14 ms  snr  30.5 dB  cv  0.02  score 1.00  Bluetooth LE 2M (GFSK)
  * burst 7     0.14 ms  snr  30.5 dB  cv  0.02  score 1.00  Bluetooth LE 2M (GFSK)
  * burst 8     0.14 ms  snr  30.5 dB  cv  0.02  score 1.00  Bluetooth LE 2M (GFSK)
  * burst 9     0.14 ms  snr  30.5 dB  cv  0.02  score 1.00  Bluetooth LE 2M (GFSK)
  * burst 10    0.14 ms  snr  30.5 dB  cv  0.02  score 1.00  Bluetooth LE 2M (GFSK)
  * burst 11    0.14 ms  snr  30.5 dB  cv  0.02  score 1.00  Bluetooth LE 2M (GFSK)
  -> 12 bursts, 12 confident. CORRECT

======================================================================
bluetooth_le2m_snr-05  --  2402.000 MHz, 56320 samples @ 8.0 MS/s
expected: Bluetooth LE 2M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================
    burst 0     7.04 ms  snr   1.2 dB  cv  0.52  score 0.29  Wi-Fi 802.11b/g (DSSS/CCK)
  -> 1 bursts, 0 confident. missed (wanted Bluetooth LE 2M)

======================================================================
bluetooth_le2m_snr-10  --  2402.000 MHz, 56320 samples @ 8.0 MS/s
expected: Bluetooth LE 2M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================
  * burst 0     7.04 ms  snr   0.7 dB  cv  0.52  score 0.43  Wi-Fi 802.11b/g (DSSS/CCK)
  -> 1 bursts, 1 confident. missed (wanted Bluetooth LE 2M)

======================================================================
SUMMARY
======================================================================
band        bursts  conf  result
bluetooth_le2m_clean      12    12  CORRECT
bluetooth_le2m_snr+00       1     0  missed (wanted Bluetooth LE 2M)
bluetooth_le2m_snr+05      12     0  missed (wanted Bluetooth LE 2M)
bluetooth_le2m_snr+10      12     0  missed (wanted Bluetooth LE 2M)
bluetooth_le2m_snr+15      12     0  missed (wanted Bluetooth LE 2M)
bluetooth_le2m_snr+20      12    12  CORRECT
bluetooth_le2m_snr+30      12    12  CORRECT
bluetooth_le2m_snr-05       1     0  missed (wanted Bluetooth LE 2M)
bluetooth_le2m_snr-10       1     1  missed (wanted Bluetooth LE 2M)
```

- Clean capture correctly identified with high accuracy - confirms FSK tone separation change was correct and not just tailored to suit the LE1M case.

- SNR-10 capture "confidently" classified pure noise as a Wi-Fi 802.11b/g (DSSS/CCK) packet. 

    - Could be due to the relatively flat envelope of DSSS/CCK which detector seems to default to if nothing else is captured - we have encountered this issue before.

    - Also symbol rate and burst length seem to line up pretty well - pure chance given it's noise.

    - Verbose capture below:

```
─── burst 0  t=0.000 ms  len=7.040 ms  SNR≈0.7 dB ───
  class          linear-shaped
  BW99 / RMS     7.924 MHz / 4.533 MHz   offset -855.5 Hz
  env CV / PAPR  0.520 / 11.0 dB   flatness 0.98  edge 0.0 dB
  symbol rate    904.8 kHz (line SNR 4.7x)
  FSK tones      2, deviation 1.268 MHz
  CSS            BW≈7.924 MHz, SF≈5, 1.962e+06 MHz/s, dechirp energy 0.12
  · symbol rate from fm-derivative
  · tone count via eye(w=1)
  candidates:
     42.9%  Wi-Fi 802.11b/g (DSSS/CCK)
            spec: IEEE 802.11-2020 cl.16/17
            · modulation linear-shaped vs dsss-psk/linear-shaped/const-env-phase: gate x1.00
            · BW99 7.924 MHz vs 14 MHz–24 MHz: 0.18
            · symbol rate 904.8 kHz vs 900 kHz–1.5 MHz: 1.00
            · burst 7.040 ms: 0.80
     20.0%  LTE / 5G NR downlink (OFDM, 15 kHz SCS)
            spec: 3GPP TS 36.211 / 38.211
            · modulation linear-shaped vs ofdm: gate x0.20
            · BW99 7.924 MHz vs 1.2 MHz–100 MHz: 1.00
            · burst 7.040 ms: 1.00
     20.0%  5G NR (OFDM, 30 kHz SCS)
            spec: 3GPP TS 38.211
            · modulation linear-shaped vs ofdm: gate x0.20
            · BW99 7.924 MHz vs 5 MHz–100 MHz: 1.00
            · burst 7.040 ms: 1.00
  * burst 0     7.04 ms  snr   0.7 dB  cv  0.52  score 0.43  Wi-Fi 802.11b/g (DSSS/CCK)
  -> 1 bursts, 1 confident. missed (wanted Bluetooth LE 2M)
```

- SNR+15 and SNR+10 packets are very low scoring - likely because of BW99 inflation issues already discussed. 

- Single verbose recording on snr+15 sample confirms suspicion:

```
======================================================================
bluetooth_le2m_snr+15  --  2402.000 MHz, 56320 samples @ 8.0 MS/s
expected: Bluetooth LE 2M (GFSK)  (GFSK)
antenna: None  gain: None dB
======================================================================

─── burst 0  t=0.711 ms  len=0.139 ms  SNR≈15.7 dB ───
  class          fsk2
  BW99 / RMS     5.704 MHz / 1.298 MHz   offset -68.37 kHz
  env CV / PAPR  0.129 / 3.3 dB   flatness 0.18  edge 17.9 dB
  symbol rate    2 MHz (line SNR 8.4x)
  FSK tones      2, deviation 511.8 kHz
  CSS            BW≈5.704 MHz, SF≈5, 1.017e+06 MHz/s, dechirp energy 0.10
  · symbol rate from fm-sign-transitions
  · tone count via eye(w=3)
  NO CONFIDENT MATCH — closest entries, all weak:
      7.5%  Bluetooth LE 2M (GFSK)
            spec: Bluetooth Core 5.4
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 5.704 MHz vs 1.6 MHz–2.6 MHz: 0.00
            · symbol rate 2 MHz vs 1.8 MHz–2.2 MHz: 1.00
            · burst 0.139 ms: 1.00
            · FSK deviation 511.8 kHz: 1.00
      3.6%  Bluetooth LE 1M (GFSK)
            spec: Bluetooth Core 5.4, Vol 6 Part B
            · modulation fsk2 vs fsk2/const-env-phase: gate x1.00
            · BW99 5.704 MHz vs 800 kHz–1.4 MHz: 0.00
            · symbol rate 2 MHz vs 900 kHz–1.1 MHz: 0.28
            · burst 0.139 ms: 1.00
            · FSK deviation 511.8 kHz: 0.10
    burst 0     0.14 ms  snr  15.7 dB  cv  0.13  score 0.07  Bluetooth LE 2M (GFSK)
  -> 1 bursts, 0 confident. missed (wanted Bluetooth LE 2M)
```

- Running pure noise through classifier to see what happens. Previously generated noise samples via `noise_baseline.py`. Ran the previously generated nosie captures through classifier and obtained results stored in `noise_out.txt`.

    - Out of 20 pure noise captures, classifier "accurately" classified a protocol on 11 of them.

    - $11/20=55%$ false positive rate.

        - On these 20 AWGN captures at 20MS/s and 11.04 ms duration.

    - BW99 was around 19.8MHz for all captures - given 20MS/s sample rate, and previously discussed BW99 issues, it lines up well with 0.99(20MHz) = 19.8 MHz.

    - Symbol rate estimation is completely random - whenever it places it by chance near the WIFI symbol rate, it scores highly.

    - Important to note that AWGN has a known envelope CV which matches measured value of 0.523 exactly. (Rayleigh envelope)

    - Other important noise-implying features: spectral_flatness = 1.00, edge = 0 dB. <- We could potentially look at that for classifying noise.

    - Underlying problem: Classification is attempted before it is established that a classifiable signal exists.