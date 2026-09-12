% gen_zigbee.m
% Generate synthetic IEEE 802.15.4 / Zigbee O-QPSK DSSS captures.
%
% Produces:
%   zigbee_oqpsk_clean
%   zigbee_oqpsk_snr+30
%   ...
%   zigbee_oqpsk_snr-10

outdir = gen_outdir();
fprintf('writing to %s\n', outdir);

% -------------------------------------------------------------
% Experiment configuration
% -------------------------------------------------------------
snrs = [Inf 30 20 15 10 5 0 -5 -10];

band_mhz = 2450;
centre_hz = 2.405e9;      % Zigbee channel 11 context

samples_per_chip = 4;

psdu_bytes = 64;
num_packets = 12;

idle_s = 1e-3;            % 1 ms between packets

% Reproducible payloads
rng(42);

% -------------------------------------------------------------
% Configure IEEE 802.15.4 O-QPSK PHY
% -------------------------------------------------------------
cfg = lrwpanOQPSKConfig( ...
    Band=band_mhz, ...
    SamplesPerChip=samples_per_chip, ...
    PSDULength=psdu_bytes);

% Trust MATLAB config for actual waveform sample rate
fs = cfg.SampleRate;

fprintf('IEEE 802.15.4 O-QPSK\n');
fprintf('  Band: %.0f MHz\n', band_mhz);
fprintf('  Fs:   %.3f MS/s\n', fs/1e6);
fprintf('  SPC:  %d\n', samples_per_chip);
fprintf('  PSDU: %d bytes\n', psdu_bytes);

idle_samples = round(idle_s * fs);

% -------------------------------------------------------------
% Generate payloads ONCE
%
% Every SNR capture therefore contains exactly the same packets.
% -------------------------------------------------------------
messages = randi([0 1], psdu_bytes*8, num_packets);

% -------------------------------------------------------------
% Generate clean packet train
% -------------------------------------------------------------
wf_clean = complex(zeros(idle_samples, 1));

for p = 1:num_packets

    packet = lrwpanWaveformGenerator(messages(:,p), cfg);

    wf_clean = [
        wf_clean;
        packet;
        complex(zeros(idle_samples, 1))
    ];
end

% Normalise peak amplitude
wf_clean = 0.8 * wf_clean / max(abs(wf_clean));

% Packet samples are non-zero; idle gaps are exactly zero.
active = abs(wf_clean) > 1e-12;

signal_power = mean(abs(wf_clean(active)).^2);

fprintf('  packet-train duration: %.2f ms\n', ...
    numel(wf_clean)/fs*1e3);

% -------------------------------------------------------------
% SNR sweep
% -------------------------------------------------------------
for k = 1:numel(snrs)

    snr_db = snrs(k);

    if isfinite(snr_db)

        noise_power = signal_power / (10^(snr_db/10));

        noise = sqrt(noise_power/2) .* ...
            (randn(size(wf_clean)) + 1j*randn(size(wf_clean)));

        wf = wf_clean + noise;

        tag = sprintf('zigbee_oqpsk_snr%+03d', snr_db);

    else

        wf = wf_clean;
        tag = 'zigbee_oqpsk_clean';

    end

    % ---------------------------------------------------------
    % Write interleaved float32 IQ
    % ---------------------------------------------------------
    base = fullfile(outdir, tag);

    fid = fopen([base '.bin'], 'w');

    iq = [real(wf).'; imag(wf).'];
    fwrite(fid, single(iq(:)), 'float32');

    fclose(fid);

    % ---------------------------------------------------------
    % Metadata
    % ---------------------------------------------------------
    meta = fopen([base '.txt'], 'w');

    fprintf(meta, 'fs_hz=%.1f\n', fs);
    fprintf(meta, 'centre_hz=%.1f\n', centre_hz);

    fprintf(meta, ...
        'expect=Zigbee / 802.15.4 O-QPSK DSSS\n');

    fprintf(meta, 'expected_mod=O-QPSK DSSS\n');
    fprintf(meta, 'source=matlab_comm_toolbox\n');

    fprintf(meta, 'band_mhz=%g\n', band_mhz);
    fprintf(meta, 'samples_per_chip=%d\n', samples_per_chip);
    fprintf(meta, 'psdu_bytes=%d\n', psdu_bytes);

    fprintf(meta, 'snr_db=%g\n', snr_db);
    fprintf(meta, 'n_samples=%d\n', numel(wf));
    fprintf(meta, 'packets=%d\n', num_packets);
    fprintf(meta, 'idle_s=%g\n', idle_s);

    fclose(meta);

    fprintf('  %-26s %d samples (%.2f ms)\n', ...
        tag, numel(wf), numel(wf)/fs*1e3);
end

fprintf('\ndone\n');