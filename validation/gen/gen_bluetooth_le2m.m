% gen_bluetooth_le2m.m
% Generate synthetic Bluetooth LE 2M GFSK captures.
%
% Produces:
%   bluetooth_le2m_clean
%   bluetooth_le2m_snr+30
%   bluetooth_le2m_snr+20
%   ...
%   bluetooth_le2m_snr-10
%
% LE2M:
%   symbol rate = 2 Msym/s
%   SamplesPerSymbol = 4
%   sample rate = 8 MS/s

outdir = gen_outdir();
fprintf('writing to %s\n', outdir);

% -------------------------------------------------------------
% Experiment parameters
% -------------------------------------------------------------
phy = "LE2M";

symbol_rate = 2e6;
samples_per_symbol = 4;
fs = symbol_rate * samples_per_symbol;   % 8 MS/s

channel_index = 37;
centre_hz = 2.402e9;

num_packets = 20;
num_message_bits = 256;

idle_s = 200e-6;
idle_samples = round(idle_s * fs);

snrs = [Inf 30 20 15 10 5 0 -5 -10];

% Reproducible payloads + noise
rng(42);

fprintf('Bluetooth %s\n', phy);
fprintf('  symbol rate: %.1f Msym/s\n', symbol_rate/1e6);
fprintf('  Fs:          %.1f MS/s\n', fs/1e6);
fprintf('  SPS:         %d\n', samples_per_symbol);
fprintf('  channel:     %d\n', channel_index);

% -------------------------------------------------------------
% Generate payloads once
%
% Every SNR capture contains exactly the same packets.
% -------------------------------------------------------------
messages = randi([0 1], num_message_bits, num_packets);

% -------------------------------------------------------------
% Generate clean packet train
% -------------------------------------------------------------
wf_clean = complex([]);

for p = 1:num_packets

    packet = bleWaveformGenerator(messages(:,p), ...
        Mode=phy, ...
        SamplesPerSymbol=samples_per_symbol, ...
        ChannelIndex=channel_index);

    wf_clean = [
        wf_clean;
        packet;
        complex(zeros(idle_samples, 1))
    ];
end

% Normalise waveform
wf_clean = 0.8 * wf_clean / max(abs(wf_clean));

% Identify packet samples, excluding exactly-zero idle regions
active = abs(wf_clean) > 1e-12;

signal_power = mean(abs(wf_clean(active)).^2);

fprintf('  signal power: %.6f\n', signal_power);
fprintf('  capture:      %.2f ms\n', numel(wf_clean)/fs*1e3);

% -------------------------------------------------------------
% Generate SNR sweep
% -------------------------------------------------------------
for k = 1:numel(snrs)

    snr_db = snrs(k);

    if isfinite(snr_db)

        % Noise power defined relative to ACTIVE signal power
        noise_power = signal_power / (10^(snr_db/10));

        noise = sqrt(noise_power/2) .* ...
            (randn(size(wf_clean)) + 1j*randn(size(wf_clean)));

        wf = wf_clean + noise;

        tag = sprintf('bluetooth_le2m_snr%+03d', snr_db);

    else

        wf = wf_clean;
        tag = 'bluetooth_le2m_clean';

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
        'expect=Bluetooth LE 2M (GFSK)\n');

    fprintf(meta, 'expected_mod=GFSK\n');
    fprintf(meta, 'source=matlab_bluetooth_toolbox\n');

    fprintf(meta, 'phy=%s\n', phy);
    fprintf(meta, 'channel_index=%d\n', channel_index);
    fprintf(meta, 'symbol_rate_hz=%.1f\n', symbol_rate);
    fprintf(meta, 'samples_per_symbol=%d\n', samples_per_symbol);

    fprintf(meta, 'snr_db=%g\n', snr_db);
    fprintf(meta, 'n_samples=%d\n', numel(wf));
    fprintf(meta, 'packets=%d\n', num_packets);
    fprintf(meta, 'message_bits=%d\n', num_message_bits);
    fprintf(meta, 'idle_s=%g\n', idle_s);

    fclose(meta);

    fprintf('  %-28s %d samples (%.2f ms)\n', ...
        tag, numel(wf), numel(wf)/fs*1e3);
end

fprintf('\ndone\n');