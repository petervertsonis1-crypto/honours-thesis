# Testing CRC-valid ADSB from `captures/`

- `envelope_cv` on crc-valid capture was measured to be lower than the 0.7 minimum gate used in `iq_protocol_id.py` 

    - Once minimum `envelope_cv` was fixed, detector could accurate classify ADSB.

- symbol rate estimation also failed.

    - Run-length method for symbol rate estimation (which is used by `iq_protocol_id.py`) requires about 3 samples per symbol for accurate estimates. ADSB at 2.4MS/s gives 1.2 samples per symbol. Accurate symbol rate estimation not possible.

    - Worth keeping in mind for future experiments.

- wrong modclass

- underlying cause for all 3 of above is sample rate. for reliable ADSB identification, higher sample rate is required. 

    - 2.4MS/s simply below pipeline's operating floor for ADSB.

# `interp_check.py`

- Trying to figure out why protocol detection couldn't identify ADSB. 

- Looking at output, envelope_cv was lower than anticipated.

    - measured 0.433 vs required 0.7 for ADSB identification gate.

- Symbol rate estimator also failed completely and returned nothing.

    - Most likely a sample rate issue - 2.4MS/s for ADSB means you get 1.2 samples per 0.5us pulse. Impossible to accurately measure symbol rate if you've only got 1 sample per symbol rate, so wasn't returning anything.

- To fix this we upsampled ADSB captures to see if that improved envelope_cv. Following cases possible:

    - Case 1 (fixable in software): the dips between pulses exist in the capture, we're just not sampling them. cv climbs toward 1.0 with interpolation.

    - Case 2 (hardware limit): the radio's filter already smoothed them away. cv stays flat no matter how fine the grid.

Results:

```shell
results:
        rate   samples      cv
       2.4 MS/s       288   0.521
       4.8 MS/s       576   0.510
       9.6 MS/s      1152   0.512
      19.2 MS/s      2304   0.512
      38.4 MS/s      4608   0.512
```

Case 2.

- Recorded CV across all those samples matches expected Rayleigh noise envelope CV (~0.523), suggests that these captures were mainly noise.

# `capture_sweep.py`

- First run was hardware limited - not 100% what went wrong exactly, but output below shows numerous errors occured during rtlsdr set up. All protocols returned identical statistics. Results were discarded but I thought it'd be important to note.

```shell
(.venv) petervertsonis@Mac thesis % python sources/capture_sweep.py --duration 0.5
9 bands, 4s of IQ, about 86 MB on disk

Found Rafael Micro R820T tuner
rtlsdr_demod_write_reg failed with -1
rtlsdr_demod_read_reg failed with -1
rtlsdr_demod_write_reg failed with -1
rtlsdr_demod_read_reg failed with -1
rtlsdr_demod_write_reg failed with -1
rtlsdr_demod_read_reg failed with -1
rtlsdr_demod_write_reg failed with -1
rtlsdr_demod_read_reg failed with -1
rtlsdr_demod_write_reg failed with -1
rtlsdr_demod_read_reg failed with -1
r82xx_write: i2c wr failed=-1 reg=05 len=7
r82xx_write: i2c wr failed=-1 reg=0c len=1
r82xx_init: failed=-1
rtlsdr_demod_write_reg failed with -1
rtlsdr_demod_read_reg failed with -1
rtlsdr_demod_write_reg failed with -1
rtlsdr_demod_read_reg failed with -1
rtlsdr_demod_write_reg failed with -1
rtlsdr_demod_read_reg failed with -1
rtlsdr_write_reg failed with -1
rtlsdr_write_reg failed with -1
Resetting device...
Found Rafael Micro R820T tuner
[INFO] Opening Generic RTL2832U OEM :: 73984474...
Found Rafael Micro R820T tuner
[adsb     ]  1090.000 MHz    0.5s  [R82XX] PLL not locked!
[INFO] Using format CF32.
  1200000 samples  peak-mean   4.7 dB   1.1s  
[fm_bcast ]   102.500 MHz    0.5s  [INFO] Using format CF32.
  1200000 samples  peak-mean   4.7 dB   1.1s  
[dab      ]   202.928 MHz    0.5s  [INFO] Using format CF32.
  1200000 samples  peak-mean   4.7 dB   1.1s  
[ais      ]   162.000 MHz    0.5s  [INFO] Using format CF32.
  1200000 samples  peak-mean   4.7 dB   1.1s  
[airband  ]   120.500 MHz    0.5s  [INFO] Using format CF32.
  1200000 samples  peak-mean   4.7 dB   1.1s  
[ism433   ]   433.920 MHz    0.5s  [INFO] Using format CF32.
  1200000 samples  peak-mean   4.7 dB   1.1s  
[ism915   ]   917.000 MHz    0.5s  [INFO] Using format CF32.
  1200000 samples  peak-mean   4.7 dB   1.1s  
[pager    ]   148.600 MHz    0.5s  [INFO] Using format CF32.
  1200000 samples  peak-mean   4.7 dB   1.1s  
[quiet    ]   250.000 MHz    0.5s  [INFO] Using format CF32.
  1200000 samples  peak-mean   4.7 dB   1.1s  

written to /Users/petervertsonis/Desktop/captures/sweep
```

- Swapped out short antenna for a longer telescopic whip. Ran again and most rtlsdr tuner issues were solved? Bit confused to be honest.

    - PLL not locked error shown for ADS-B.

    - I didn't worry about this because I have already tested the detector with ADS-B. See captures/ for a list of previously acquired ADSB captures.

- Important to note in the output below, since I switched to a longer antenna (~1m telescopic whip), we expect better captures for lower frequencies signals. 

- This can be seen in the trace below where ism433 & ism915 were recorded around 8.5dB, corresponding to the noise floor.

- Protocols that I think were successfully 

```shell
(.venv) petervertsonis@Mac thesis % python sources/capture_sweep.py --duration 0.5
9 bands, 4s of IQ, about 86 MB on disk

Found Rafael Micro R820T tuner
[INFO] Opening Generic RTL2832U OEM :: 73984474...
Found Rafael Micro R820T tuner
[adsb     ]  1090.000 MHz    0.5s  [R82XX] PLL not locked!
[INFO] Using format CF32.
  1200000 samples  peak-mean   8.3 dB   1.1s  
[fm_bcast ]   102.500 MHz    0.5s  [INFO] Using format CF32.
  1200000 samples  peak-mean   4.8 dB   1.1s  
[dab      ]   202.928 MHz    0.5s  [INFO] Using format CF32.
  1200000 samples  peak-mean   4.3 dB   1.1s  
[ais      ]   162.000 MHz    0.5s  [INFO] Using format CF32.
  1200000 samples  peak-mean  10.7 dB   1.1s  
[airband  ]   120.500 MHz    0.5s  [INFO] Using format CF32.
  1200000 samples  peak-mean  10.3 dB   1.1s  
[ism433   ]   433.920 MHz    0.5s  [INFO] Using format CF32.
  1200000 samples  peak-mean   8.6 dB   1.1s  
[ism915   ]   917.000 MHz    0.5s  [INFO] Using format CF32.
  1200000 samples  peak-mean   8.4 dB   1.1s  
[pager    ]   148.600 MHz    0.5s  [INFO] Using format CF32.
  1200000 samples  peak-mean  15.6 dB   1.1s  
[quiet    ]   250.000 MHz    0.5s  [INFO] Using format CF32.
  1200000 samples  peak-mean   7.5 dB   1.1s  

written to /Users/petervertsonis/Desktop/thesis/captures/sweep
```

# `run_sweep_id.py`

## First attempt at feeding in ais, pager, fm broadcast and dab into protocol detection:

```shell
(.venv) petervertsonis@Mac thesis % python validation/experiments/run_sweep_id.py --only ais pager fm_bcast dab --max-samples 4800000

======================================================================
ais  --  162.000 MHz, 4800000 samples @ 2.4 MS/s
expected: AIS  (GMSK)
antenna: whip  gain: 40.0 dB
======================================================================
    burst 0     2.66 ms  snr   6.9 dB  cv  1.07  score   -   (nothing scored)
  -> 1 bursts, 0 confident. missed (wanted AIS)

======================================================================
dab  --  202.928 MHz, 4800000 samples @ 2.4 MS/s
expected: DAB+  (OFDM (DQPSK))
antenna: whip  gain: 35.0 dB
======================================================================
  * burst 0  2000.00 ms  snr   0.3 dB  cv  0.42  score 0.78  DAB+ (OFDM, 1 kHz SCS)
  -> 1 bursts, 1 confident. CORRECT

======================================================================
fm_bcast  --  102.500 MHz, 4800000 samples @ 2.4 MS/s
expected: FM broadcast  (WBFM)
antenna: whip  gain: 25.0 dB
======================================================================
    burst 0  2000.00 ms  snr   0.2 dB  cv  0.46  score   -   (nothing scored)
  -> 1 bursts, 0 confident. missed (wanted FM broadcast)

======================================================================
pager  --  148.600 MHz, 4800000 samples @ 2.4 MS/s
expected: POCSAG paging  (2-FSK)
antenna: whip  gain: 32.0 dB
======================================================================
no bursts extracted

======================================================================
SUMMARY
======================================================================
band        bursts  conf  result
ais              1     0  missed (wanted AIS)
dab              1     1  CORRECT
fm_bcast         1     0  missed (wanted FM broadcast)
pager            0  None  no bursts
```

- DAB successfully identified!

    - Informative -> OFDM detection via cyclic prefix autocorrelation worked on a live, unlabelled capture. 

- Ran --verbose on DAB capture to see specifically what led to the classification.

    - For flat signals - RMS width and true width differ by about 3.46x (RMS = 0.289T). 945.2 / 2 = 472.6 x 3.464 = 1.64 MHz, which is closer to expected DAB bandwidth.

        - BW99 can be dragged wide by noise - RMS bandwidth isn't. Important to remember.

```
(.venv) petervertsonis@Mac thesis % python validation/experiments/run_sweep_id.py --only dab --max-samples 4800000 --verbose

======================================================================
dab  --  202.928 MHz, 4800000 samples @ 2.4 MS/s
expected: DAB+  (OFDM (DQPSK))
antenna: whip  gain: 35.0 dB
======================================================================

─── burst 0  t=0.000 ms  len=2000.000 ms  SNR≈0.3 dB ───
  class          ofdm
  BW99 / RMS     2.175 MHz / 945.2 kHz   offset 68.87 kHz
  env CV / PAPR  0.424 / 5.4 dB   flatness 0.56  edge 12.7 dB
  symbol rate    50.13 kHz (line SNR 6.0x)
  FSK tones      1, deviation 0 Hz
  OFDM           FFT≈2400 samp, CP≈600, SCS≈1 kHz (z=444.1)
  repetition     period 119 samp (rho 0.36), CFO -1695 Hz mod 20.17 kHz
  CSS            BW≈2.175 MHz, SF≈5, 1.478e+05 MHz/s, dechirp energy 0.11
  · repeating structure at 119 samples (rho 0.36); CFO -1695 Hz modulo 20168 Hz
  · symbol rate from squared-envelope
  · tone count via blanket(w=24)
  candidates:
     77.8%  DAB+ (OFDM, 1 kHz SCS)
            spec: ETSI EN 300 401
            · modulation ofdm vs ofdm: gate x1.00
            · BW99 2.175 MHz vs 1.4 MHz–1.6 MHz: 0.56
            · burst 2000.000 ms: 1.00
            · subcarrier spacing 1 kHz: 1.00
  * burst 0  2000.00 ms  snr   0.3 dB  cv  0.42  score 0.78  DAB+ (OFDM, 1 kHz SCS)
  -> 1 bursts, 1 confident. CORRECT

======================================================================
SUMMARY
======================================================================
band        bursts  conf  result
dab              1     1  CORRECT
```

- FM Broadcast fail -> no AM/analog voice entry; WBFM present but not scored above floor

    - Still a reliable capture - peak - mean was 4.8dB so a continuous broadcast signal was more than likely present. Need to look at protocol detection logic for FM detection.

- Pager and AIS failed. No correct detections? 

    - Inconclusive - can't confirm if anything was actually received during the captures.

    - Worth noting that I'm in Greenacre and probably note the optimal location to receive AIS signals.

    - Pager is sus - should be able to pick that up. 

        - Results inconclusive, capture confounded by mid-experiment gain change (in an attempt to reduce clipping), frequency was never verified.

        - POCSAG frequencies are genuinely NOT well documented. 

## Feeding full length ais and pager captures in

- Max samples 4800000 was truncating to first 2s of 10-15s captures for ais and pager. Maybe we're cutting all the good transmissions out?

```shell
(.venv) petervertsonis@Mac thesis % python validation/experiments/run_sweep_id.py --only ais pager

======================================================================
ais  --  162.000 MHz, 24000000 samples @ 2.4 MS/s
expected: AIS  (GMSK)
antenna: whip  gain: 40.0 dB
======================================================================
    burst 0     2.66 ms  snr   6.9 dB  cv  1.07  score   -   (nothing scored)
    burst 1     0.33 ms  snr   6.4 dB  cv  1.06  score   -   (nothing scored)
    burst 2     0.41 ms  snr   6.3 dB  cv  1.04  score   -   (nothing scored)
    burst 3     2.95 ms  snr   6.9 dB  cv  1.08  score   -   (nothing scored)
    burst 4     3.04 ms  snr   6.2 dB  cv  0.97  score   -   (nothing scored)
    burst 5     0.05 ms  snr   4.5 dB  cv  0.93  score   -   (nothing scored)
  -> 6 bursts, 0 confident. missed (wanted AIS)

======================================================================
pager  --  148.600 MHz, 36000000 samples @ 2.4 MS/s
expected: POCSAG paging  (2-FSK)
antenna: whip  gain: 32.0 dB
======================================================================
no bursts extracted

======================================================================
SUMMARY
======================================================================
band        bursts  conf  result
ais              6     0  missed (wanted AIS)
pager            0  None  no bursts
```

- Envelope CV for AIS signals being around 1 is sus - AIS is GMSK which maintains a constant envelope so CV should be low. Being around 1 means a spiky transmission. Longest burst was around 3ms - AIS is 256 bits at 9600 bps ~ 27ms.

    - New hypothesis: detector is finding impulsive broadband interference while AIS itself is buried. 

    - AIS is 14kHz wide inside a 2.4MHz capture. `detect_bursts()` measures the full band power, so the signal contributes about 0.6% of bandwidth and the rest is noise. POCSAG will have the same problem.

    - DAB is ~1.5MHz so fills most of the available bandwidth - not an issue here.

# `narrowband_check.py`

- More bursts detected - `run_sweep_id.py` discarding all but 12 longest bursts. Not wrong, but deceptive. More true bursts than originally expected.

- Spectral flatness measurements point to captures being all noise.

```shell
(.venv) petervertsonis@Mac thesis % python validation/experiments/narrowband_check.py ais --offset -25000
ais: 162.000 MHz, 24000000 samples @ 2.4 MS/s
expected AIS, shifting -25.0 kHz to DC

spectrum before/after:
  wideband   peak at   -863.1 kHz   spectral flatness 0.896   (flat/impulsive)
  channelised to 48.0 kS/s, 480000 samples
  narrowband peak at     22.2 kHz   spectral flatness 0.967   (flat/impulsive)

bursts at 2.4 MS/s: 7818   (noise floor -24.8 dB)
bursts at 48.0 kS/s:    8   (noise floor -40.5 dB)

identify() on the channelised signal:
(.venv) petervertsonis@Mac thesis % python validation/experiments/narrowband_check.py ais --offset 25000 
ais: 162.000 MHz, 24000000 samples @ 2.4 MS/s
expected AIS, shifting +25.0 kHz to DC

spectrum before/after:
  wideband   peak at   -863.1 kHz   spectral flatness 0.896   (flat/impulsive)
  channelised to 48.0 kS/s, 480000 samples
  narrowband peak at    -17.3 kHz   spectral flatness 0.964   (flat/impulsive)

bursts at 2.4 MS/s: 7818   (noise floor -24.8 dB)
bursts at 48.0 kS/s:    7   (noise floor -41.3 dB)

identify() on the channelised signal:
    burst 0     1.85 ms  snr   7.2 dB  cv  0.50  score   -   (nothing scored)
(.venv) petervertsonis@Mac thesis % python validation/experiments/narrowband_check.py pager             
pager: 148.600 MHz, 36000000 samples @ 2.4 MS/s
expected POCSAG paging, shifting +0.0 kHz to DC

spectrum before/after:
  wideband   peak at   -458.2 kHz   spectral flatness 0.920   (flat/impulsive)
  channelised to 48.0 kS/s, 720000 samples
  narrowband peak at     -8.3 kHz   spectral flatness 0.981   (flat/impulsive)

bursts at 2.4 MS/s: 140625   (noise floor -25.7 dB)
bursts at 48.0 kS/s:   79   (noise floor -37.6 dB)

identify() on the channelised signal:
```

- Ran same test on known quiet / no protocol. Result below shows `detect_burst()` detecting a peak at 11kHz? Unknown.

```shell
(.venv) petervertsonis@Mac thesis % python validation/experiments/narrowband_check.py quiet
quiet: 250.000 MHz, 4800000 samples @ 2.4 MS/s
expected nothing, shifting +0.0 kHz to DC

spectrum before/after:
  wideband   peak at     11.1 kHz   spectral flatness 0.846   (flat/impulsive)
  channelised to 48.0 kS/s, 96000 samples
  narrowband peak at     11.2 kHz   spectral flatness 0.239   (structured)

bursts at 2.4 MS/s:    1   (noise floor -6.9 dB)
bursts at 48.0 kS/s:    1   (noise floor -18.4 dB)

identify() on the channelised signal:
    burst 0  2000.00 ms  snr   0.6 dB  cv  0.37  score   -   (nothing scored)
```

# MATLAB WLAN Toolbox WiFi Generation

## Initial testing

- `gen_wifi.m` MATLAB script was used to generate Wi-Fi 802.11g/n/ax at various different SNR (inf, 30, 20, 15, 10, 5, 0)

- binary outputs were then converted into .npy which our pipeline is built for using `wifi_to_npy.py`.

- these .npy outputs were fed into `run_sweep_id.py` and produced the below output:

```shell
(.venv) petervertsonis@Mac thesis % python validation/experiments/run_sweep_id.py --dir generated

======================================================================
wifi_ht20_clean  --  2437.000 MHz, 220800 samples @ 20.0 MS/s
expected: Wi-Fi 802.11g/n/ax 20 MHz (OFDM)  (OFDM (16-QAM))
antenna: None  gain: None dB
======================================================================
  * burst 0     0.32 ms  snr 187.6 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 1     0.32 ms  snr 187.6 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 2     0.32 ms  snr 187.6 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 3     0.32 ms  snr 187.6 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 4     0.32 ms  snr 187.6 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 5     0.32 ms  snr 187.6 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 6     0.32 ms  snr 187.6 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 7     0.32 ms  snr 187.6 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 8     0.32 ms  snr 187.6 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 9     0.32 ms  snr 187.6 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 10    0.32 ms  snr 187.6 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 11    0.32 ms  snr 187.6 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  -> 12 bursts, 12 confident. CORRECT

======================================================================
wifi_ht20_snr00  --  2437.000 MHz, 220800 samples @ 20.0 MS/s
expected: Wi-Fi 802.11g/n/ax 20 MHz (OFDM)  (OFDM (16-QAM))
antenna: None  gain: None dB
======================================================================
  * burst 0    11.04 ms  snr   3.2 dB  cv  0.57  score 0.91  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  -> 1 bursts, 1 confident. CORRECT

======================================================================
wifi_ht20_snr05  --  2437.000 MHz, 220800 samples @ 20.0 MS/s
expected: Wi-Fi 802.11g/n/ax 20 MHz (OFDM)  (OFDM (16-QAM))
antenna: None  gain: None dB
======================================================================
  * burst 0     0.32 ms  snr   8.0 dB  cv  0.51  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 1     0.32 ms  snr   8.0 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 2     0.32 ms  snr   8.0 dB  cv  0.51  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 3     0.32 ms  snr   8.0 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 4     0.32 ms  snr   8.0 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 5     0.32 ms  snr   8.0 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 6     0.32 ms  snr   8.0 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 7     0.32 ms  snr   8.1 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 8     0.32 ms  snr   8.0 dB  cv  0.51  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 9     0.32 ms  snr   8.0 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 10    0.32 ms  snr   8.0 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 11    0.32 ms  snr   8.0 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  -> 12 bursts, 12 confident. CORRECT

======================================================================
wifi_ht20_snr10  --  2437.000 MHz, 220800 samples @ 20.0 MS/s
expected: Wi-Fi 802.11g/n/ax 20 MHz (OFDM)  (OFDM (16-QAM))
antenna: None  gain: None dB
======================================================================
  * burst 0     0.32 ms  snr  12.5 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 1     0.32 ms  snr  12.5 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 2     0.32 ms  snr  12.5 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 3     0.32 ms  snr  12.5 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 4     0.32 ms  snr  12.5 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 5     0.32 ms  snr  12.5 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 6     0.32 ms  snr  12.5 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 7     0.32 ms  snr  12.5 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 8     0.32 ms  snr  12.5 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 9     0.32 ms  snr  12.5 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 10    0.32 ms  snr  12.5 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 11    0.32 ms  snr  12.5 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  -> 12 bursts, 12 confident. CORRECT

======================================================================
wifi_ht20_snr15  --  2437.000 MHz, 220800 samples @ 20.0 MS/s
expected: Wi-Fi 802.11g/n/ax 20 MHz (OFDM)  (OFDM (16-QAM))
antenna: None  gain: None dB
======================================================================
  * burst 0     0.32 ms  snr  17.3 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 1     0.32 ms  snr  17.3 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 2     0.32 ms  snr  17.3 dB  cv  0.51  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 3     0.32 ms  snr  17.3 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 4     0.32 ms  snr  17.3 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 5     0.32 ms  snr  17.3 dB  cv  0.51  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 6     0.32 ms  snr  17.3 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 7     0.32 ms  snr  17.3 dB  cv  0.51  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 8     0.32 ms  snr  17.3 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 9     0.32 ms  snr  17.3 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 10    0.32 ms  snr  17.3 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 11    0.32 ms  snr  17.3 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  -> 12 bursts, 12 confident. CORRECT

======================================================================
wifi_ht20_snr20  --  2437.000 MHz, 220800 samples @ 20.0 MS/s
expected: Wi-Fi 802.11g/n/ax 20 MHz (OFDM)  (OFDM (16-QAM))
antenna: None  gain: None dB
======================================================================
  * burst 0     0.32 ms  snr  22.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 1     0.32 ms  snr  22.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 2     0.32 ms  snr  22.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 3     0.32 ms  snr  22.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 4     0.32 ms  snr  22.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 5     0.32 ms  snr  22.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 6     0.32 ms  snr  22.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 7     0.32 ms  snr  22.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 8     0.32 ms  snr  22.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 9     0.32 ms  snr  22.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 10    0.32 ms  snr  22.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 11    0.32 ms  snr  22.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  -> 12 bursts, 12 confident. CORRECT

======================================================================
wifi_ht20_snr30  --  2437.000 MHz, 220800 samples @ 20.0 MS/s
expected: Wi-Fi 802.11g/n/ax 20 MHz (OFDM)  (OFDM (16-QAM))
antenna: None  gain: None dB
======================================================================
  * burst 0     0.32 ms  snr  32.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 1     0.32 ms  snr  32.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 2     0.32 ms  snr  32.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 3     0.32 ms  snr  32.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 4     0.32 ms  snr  32.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 5     0.32 ms  snr  32.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 6     0.32 ms  snr  32.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 7     0.32 ms  snr  32.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 8     0.32 ms  snr  32.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 9     0.32 ms  snr  32.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 10    0.32 ms  snr  32.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  * burst 11    0.32 ms  snr  32.2 dB  cv  0.52  score 1.00  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  -> 12 bursts, 12 confident. CORRECT

======================================================================
SUMMARY
======================================================================
band        bursts  conf  result
wifi_ht20_clean      12    12  CORRECT
wifi_ht20_snr00       1     1  CORRECT
wifi_ht20_snr05      12    12  CORRECT
wifi_ht20_snr10      12    12  CORRECT
wifi_ht20_snr15      12    12  CORRECT
wifi_ht20_snr20      12    12  CORRECT
wifi_ht20_snr30      12    12  CORRECT
```

- NOTE: envelope CV is identical across all bursts at all tested SNRs. This is because the 52 active subcarriers summed gives complex gaussian by central limit theorem, so `|x|` is Rayleigh distributed - and Rayleigh noise has CV = 0.523. SNR only increases the amount of noise - gaussian + gaussian = gaussian, so no matter the SNR, the envelope will stay Rayleigh, and thus envelope_cv is a meaningless statistic.

    - Envelope CV is incapable of responding to noise for an OFDM signal. <- verbose check of snr00 capture saw envelope_cv of 0.572??

```
(.venv) petervertsonis@Mac thesis % python validation/experiments/run_sweep_id.py --dir generated --only wifi_ht20_snr00 --verbose

======================================================================
wifi_ht20_snr00  --  2437.000 MHz, 220800 samples @ 20.0 MS/s
expected: Wi-Fi 802.11g/n/ax 20 MHz (OFDM)  (OFDM (16-QAM))
antenna: None  gain: None dB
======================================================================

─── burst 0  t=0.000 ms  len=11.040 ms  SNR≈3.2 dB ───
  class          ofdm
  BW99 / RMS     19.61 MHz / 10.96 MHz   offset -1.392 kHz
  env CV / PAPR  0.572 / 11.7 dB   flatness 0.94  edge 0.0 dB
  symbol rate    3.822 MHz (line SNR 8.1x)
  FSK tones      1, deviation 0 Hz
  OFDM           FFT≈64 samp, CP≈16, SCS≈312.5 kHz (z=54.1)
  repetition     period 16 samp (rho 0.71), CFO +5180 Hz mod 1.25 MHz
  CSS            BW≈19.61 MHz, SF≈5, 1.201e+07 MHz/s, dechirp energy 0.13
  · repeating structure at 16 samples (rho 0.71); CFO +5180 Hz modulo 1250000 Hz
  · symbol rate from squared-envelope
  · tone count via blanket(w=3)
  candidates:
     91.1%  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
            spec: IEEE 802.11-2020 cl.17/19/27
            · modulation ofdm vs ofdm: gate x1.00
            · BW99 19.61 MHz vs 15 MHz–20.5 MHz: 1.00
            · burst 11.040 ms: 0.65
            · subcarrier spacing 312.5 kHz: 1.00
     50.2%  Wi-Fi 802.11n/ac/ax 40 MHz
            spec: IEEE 802.11-2020
            · modulation ofdm vs ofdm: gate x1.00
            · BW99 19.61 MHz vs 33 MHz–41 MHz: 0.25
            · burst 11.040 ms: 0.65
            · subcarrier spacing 312.5 kHz: 1.00
      8.5%  LTE / 5G NR downlink (OFDM, 15 kHz SCS)
            spec: 3GPP TS 36.211 / 38.211
            · modulation ofdm vs ofdm: gate x1.00
            · BW99 19.61 MHz vs 1.2 MHz–100 MHz: 1.00
            · burst 11.040 ms: 1.00
            · subcarrier spacing 312.5 kHz: 0.00
  * burst 0    11.04 ms  snr   3.2 dB  cv  0.57  score 0.91  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  -> 1 bursts, 1 confident. CORRECT
```

 ## Testing lower SNR (-5, -10, -15)

- 0dB SNR included for reference

```
(.venv) petervertsonis@Mac thesis % python validation/experiments/run_sweep_id.py --dir generated --only wifi_ht20_snr-5 wifi_ht20_snr-10 wifi_ht20_snr-1
5 wifi_ht20_snr00

======================================================================
wifi_ht20_snr-10  --  2437.000 MHz, 220800 samples @ 20.0 MS/s
expected: Wi-Fi 802.11g/n/ax 20 MHz (OFDM)  (OFDM (16-QAM))
antenna: None  gain: None dB
======================================================================
    burst 0    11.04 ms  snr   0.7 dB  cv  0.52  score 0.20  LTE / 5G NR downlink (OFDM, 15 kHz SCS)
  -> 1 bursts, 0 confident. missed (wanted Wi-Fi 802.11g/n/ax 20 MHz)

======================================================================
wifi_ht20_snr-15  --  2437.000 MHz, 220800 samples @ 20.0 MS/s
expected: Wi-Fi 802.11g/n/ax 20 MHz (OFDM)  (OFDM (16-QAM))
antenna: None  gain: None dB
======================================================================
  * burst 0    11.04 ms  snr   0.4 dB  cv  0.52  score 0.87  Wi-Fi 802.11b/g (DSSS/CCK)
  -> 1 bursts, 1 confident. missed (wanted Wi-Fi 802.11g/n/ax 20 MHz)

======================================================================
wifi_ht20_snr-5  --  2437.000 MHz, 220800 samples @ 20.0 MS/s
expected: Wi-Fi 802.11g/n/ax 20 MHz (OFDM)  (OFDM (16-QAM))
antenna: None  gain: None dB
======================================================================
  * burst 0    11.04 ms  snr   1.4 dB  cv  0.53  score 0.91  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  -> 1 bursts, 1 confident. CORRECT

======================================================================
wifi_ht20_snr00  --  2437.000 MHz, 220800 samples @ 20.0 MS/s
expected: Wi-Fi 802.11g/n/ax 20 MHz (OFDM)  (OFDM (16-QAM))
antenna: None  gain: None dB
======================================================================
  * burst 0    11.04 ms  snr   3.2 dB  cv  0.57  score 0.91  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  -> 1 bursts, 1 confident. CORRECT

======================================================================
SUMMARY
======================================================================
band        bursts  conf  result
wifi_ht20_snr-10       1     0  missed (wanted Wi-Fi 802.11g/n/ax 20 MHz)
wifi_ht20_snr-15       1     1  missed (wanted Wi-Fi 802.11g/n/ax 20 MHz)
wifi_ht20_snr-5       1     1  CORRECT
wifi_ht20_snr00       1     1  CORRECT
```

- Verbose run on (-5, -10, -15) dB SNR:

```
(.venv) petervertsonis@Mac thesis % python validation/experiments/run_sweep_id.py --dir generated --only wifi_ht20_snr-5 wifi_ht20_snr-10 wifi_ht20_snr-15 --verbose

======================================================================
wifi_ht20_snr-10  --  2437.000 MHz, 220800 samples @ 20.0 MS/s
expected: Wi-Fi 802.11g/n/ax 20 MHz (OFDM)  (OFDM (16-QAM))
antenna: None  gain: None dB
======================================================================

─── burst 0  t=0.000 ms  len=11.040 ms  SNR≈0.7 dB ───
  class          linear-shaped
  BW99 / RMS     19.77 MHz / 11.44 MHz   offset -6.692 kHz
  env CV / PAPR  0.523 / 11.4 dB   flatness 0.99  edge 0.0 dB
  symbol rate    7.909 MHz (line SNR 4.4x)
  FSK tones      1, deviation 0 Hz
  CSS            BW≈19.77 MHz, SF≈5, 1.222e+07 MHz/s, dechirp energy 0.11
  · symbol rate from fm-sign-transitions
  · tone count via blanket(w=1)
  NO CONFIDENT MATCH — closest entries, all weak:
     20.0%  LTE / 5G NR downlink (OFDM, 15 kHz SCS)
            spec: 3GPP TS 36.211 / 38.211
            · modulation linear-shaped vs ofdm: gate x0.20
            · BW99 19.77 MHz vs 1.2 MHz–100 MHz: 1.00
            · burst 11.040 ms: 1.00
     20.0%  5G NR (OFDM, 30 kHz SCS)
            spec: 3GPP TS 38.211
            · modulation linear-shaped vs ofdm: gate x0.20
            · BW99 19.77 MHz vs 5 MHz–100 MHz: 1.00
            · burst 11.040 ms: 1.00
     17.3%  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
            spec: IEEE 802.11-2020 cl.17/19/27
            · modulation linear-shaped vs ofdm: gate x0.20
            · BW99 19.77 MHz vs 15 MHz–20.5 MHz: 1.00
            · burst 11.040 ms: 0.65
    burst 0    11.04 ms  snr   0.7 dB  cv  0.52  score 0.20  LTE / 5G NR downlink (OFDM, 15 kHz SCS)
  -> 1 bursts, 0 confident. missed (wanted Wi-Fi 802.11g/n/ax 20 MHz)

======================================================================
wifi_ht20_snr-15  --  2437.000 MHz, 220800 samples @ 20.0 MS/s
expected: Wi-Fi 802.11g/n/ax 20 MHz (OFDM)  (OFDM (16-QAM))
antenna: None  gain: None dB
======================================================================

─── burst 0  t=0.000 ms  len=11.040 ms  SNR≈0.4 dB ───
  class          linear-shaped
  BW99 / RMS     19.8 MHz / 11.52 MHz   offset -9.078 kHz
  env CV / PAPR  0.523 / 10.9 dB   flatness 0.99  edge 0.0 dB
  symbol rate    1.133 MHz (line SNR 4.5x)
  FSK tones      1, deviation 0 Hz
  CSS            BW≈19.8 MHz, SF≈5, 1.225e+07 MHz/s, dechirp energy 0.11
  · symbol rate from squared-envelope
  · tone count via blanket(w=9)
  candidates:
     86.9%  Wi-Fi 802.11b/g (DSSS/CCK)
            spec: IEEE 802.11-2020 cl.16/17
            · modulation linear-shaped vs dsss-psk/linear-shaped/const-env-phase: gate x1.00
            · BW99 19.8 MHz vs 14 MHz–24 MHz: 1.00
            · symbol rate 1.133 MHz vs 900 kHz–1.5 MHz: 1.00
            · burst 11.040 ms: 0.54
     20.0%  LTE / 5G NR downlink (OFDM, 15 kHz SCS)
            spec: 3GPP TS 36.211 / 38.211
            · modulation linear-shaped vs ofdm: gate x0.20
            · BW99 19.8 MHz vs 1.2 MHz–100 MHz: 1.00
            · burst 11.040 ms: 1.00
     20.0%  5G NR (OFDM, 30 kHz SCS)
            spec: 3GPP TS 38.211
            · modulation linear-shaped vs ofdm: gate x0.20
            · BW99 19.8 MHz vs 5 MHz–100 MHz: 1.00
            · burst 11.040 ms: 1.00
  * burst 0    11.04 ms  snr   0.4 dB  cv  0.52  score 0.87  Wi-Fi 802.11b/g (DSSS/CCK)
  -> 1 bursts, 1 confident. missed (wanted Wi-Fi 802.11g/n/ax 20 MHz)

======================================================================
wifi_ht20_snr-5  --  2437.000 MHz, 220800 samples @ 20.0 MS/s
expected: Wi-Fi 802.11g/n/ax 20 MHz (OFDM)  (OFDM (16-QAM))
antenna: None  gain: None dB
======================================================================

─── burst 0  t=0.000 ms  len=11.040 ms  SNR≈1.4 dB ───
  class          ofdm
  BW99 / RMS     19.74 MHz / 11.26 MHz   offset -10.52 kHz
  env CV / PAPR  0.532 / 11.7 dB   flatness 0.98  edge 0.0 dB
  symbol rate    7.426 MHz (line SNR 4.7x)
  FSK tones      1, deviation 0 Hz
  OFDM           FFT≈64 samp, CP≈2, SCS≈312.5 kHz (z=44.4)
  CSS            BW≈19.74 MHz, SF≈5, 1.218e+07 MHz/s, dechirp energy 0.12
  · symbol rate from fm-sign-transitions
  · tone count via blanket(w=1)
  candidates:
     91.1%  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
            spec: IEEE 802.11-2020 cl.17/19/27
            · modulation ofdm vs ofdm: gate x1.00
            · BW99 19.74 MHz vs 15 MHz–20.5 MHz: 1.00
            · burst 11.040 ms: 0.65
            · subcarrier spacing 312.5 kHz: 1.00
     51.0%  Wi-Fi 802.11n/ac/ax 40 MHz
            spec: IEEE 802.11-2020
            · modulation ofdm vs ofdm: gate x1.00
            · BW99 19.74 MHz vs 33 MHz–41 MHz: 0.26
            · burst 11.040 ms: 0.65
            · subcarrier spacing 312.5 kHz: 1.00
      8.5%  LTE / 5G NR downlink (OFDM, 15 kHz SCS)
            spec: 3GPP TS 36.211 / 38.211
            · modulation ofdm vs ofdm: gate x1.00
            · BW99 19.74 MHz vs 1.2 MHz–100 MHz: 1.00
            · burst 11.040 ms: 1.00
            · subcarrier spacing 312.5 kHz: 0.00
  * burst 0    11.04 ms  snr   1.4 dB  cv  0.53  score 0.91  Wi-Fi 802.11g/n/ax 20 MHz (OFDM)
  -> 1 bursts, 1 confident. CORRECT

======================================================================
SUMMARY
======================================================================
band        bursts  conf  result
wifi_ht20_snr-10       1     0  missed (wanted Wi-Fi 802.11g/n/ax 20 MHz)
wifi_ht20_snr-15       1     1  missed (wanted Wi-Fi 802.11g/n/ax 20 MHz)
wifi_ht20_snr-5       1     1  CORRECT
```

- Running --verbose on DAB captures raised issue - program was stalling on larger captures. likely because `iq_protocol_id.py` runs `raw = np.convolve(prod, np.ones(window), mode="valid")` (line 359) combined with `window = min(n_repeats * tau, x.size - tau - 1)` (line 443) and the fact that `tau` is allowed to run up to `x.size // (n_repeats + 1)` means that for large bursts, window can approach segment length -> O(n^2)

- Possible fix below, not yet implemented (lines 361-362 already do this). O(n) alternative.

```
prod = x[:-tau] * np.conj(x[tau:])
cs_p = np.concatenate(([0.0 + 0.0j], np.cumsum(prod)))
raw = cs_p[window:] - cs_p[:-window]
```

