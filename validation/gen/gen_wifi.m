% gen_wifi.m -- generate 802.11 waveforms for Philip's protocol ID pipeline.
%
% Writes interleaved float32 IQ (.bin) plus a small text sidecar. Run
% wifi_to_npy.py afterwards to convert into the npy+json pair that
% run_sweep_id.py already understands.
%
% WHY GENERATE: the RTL-SDR tops out near 1.766 GHz, so 2.4 GHz Wi-Fi is
% physically unreachable. Generated signals also give known ground truth and
% a controllable SNR, which real captures could not.
%
% SAMPLE RATE: a 20 MHz Wi-Fi channel needs 20 MS/s. Do NOT decimate toward
% 2.4 MS/s -- that reproduces exactly the samples-per-symbol failure we found
% with ADS-B. Keep the native rate and pass it through to identify().

here   = fileparts(mfilename('fullpath'));   % .../thesis/validation/gen
repo   = fileparts(fileparts(here));         % .../thesis
outdir = fullfile(repo, 'captures', 'generated');
if ~exist(outdir, 'dir'); mkdir(outdir); end

fprintf('writing to %s\n', outdir);

% SNR sweep. Inf means noiseless. This is the part real captures can't do:
% the same known signal at a controlled noise level, so the detection
% threshold can actually be located rather than guessed at.
snrs = [Inf 30 20 15 10 5 0 -5 -10 -15];

cfg = wlanHTConfig( ...
    'ChannelBandwidth', 'CBW20', ...
    'NumTransmitAntennas', 1, ...
    'NumSpaceTimeStreams', 1, ...
    'MCS', 3, ...                    % 16-QAM, rate 1/2
    'PSDULength', 1024);

fs = wlanSampleRate(cfg);            % 20e6 for CBW20
fprintf('sample rate: %.1f MS/s\n', fs/1e6);

for k = 1:numel(snrs)
    snr = snrs(k);

    % Idle time between packets matters. Without gaps the waveform is
    % continuous, detect_bursts() takes its continuous fallback, and you get
    % one burst spanning everything -- which is what stalled the 433/917 MHz
    % runs. 200 us of idle gives the segmenter something to find.
    bits = randi([0 1], cfg.PSDULength * 8, 1);
    wf = wlanWaveformGenerator(bits, cfg, ...
        'NumPackets', 20, ...
        'IdleTime', 200e-6);

    % scale to roughly match the RTL-SDR captures (peak near 0.8)
    wf = 0.8 * wf / max(abs(wf));

    if isfinite(snr)
        wf = awgn(wf, snr, 'measured');
        tag = sprintf('snr%02d', snr);
    else
        tag = 'clean';
    end

    base = fullfile(outdir, sprintf('wifi_ht20_%s', tag));

    fid = fopen([base '.bin'], 'w');
    iq = [real(wf).'; imag(wf).'];       % interleave I,Q,I,Q...
    fwrite(fid, single(iq(:)), 'float32');
    fclose(fid);

    meta = fopen([base '.txt'], 'w');
    fprintf(meta, 'fs_hz=%.1f\n', fs);
    fprintf(meta, 'expect=Wi-Fi 802.11g/n/ax 20 MHz (OFDM)\n');
    fprintf(meta, 'expected_mod=OFDM (16-QAM)\n');
    fprintf(meta, 'snr_db=%g\n', snr);
    fprintf(meta, 'n_samples=%d\n', numel(wf));
    fprintf(meta, 'packets=20\n');
    fprintf(meta, 'idle_s=200e-6\n');
    fclose(meta);

    fprintf('  %s: %d samples\n', tag, numel(wf));
end

fprintf('done -- now run: python validation/tools/wifi_to_npy.py\n');