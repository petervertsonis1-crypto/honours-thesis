% gen_bluetooth_classic.m
% Generate synthetic Bluetooth Classic Basic Rate (BR) GFSK captures.
%
% Produces:
%   bluetooth_br_clean
%   bluetooth_br_snr+30
%   bluetooth_br_snr+20
%   ...
%   bluetooth_br_snr-10
%
% Bluetooth Classic BR:
%   symbol rate = 1 Msym/s
%   SamplesPerSymbol = 8
%   sample rate = 8 MS/s

outdir = gen_outdir();
fprintf('writing to %s\n', outdir);

% -------------------------------------------------------------
% Experiment parameters
% -------------------------------------------------------------

phy = "BR";

symbol_rate = 1e6;
samples_per_symbol = 8;
fs = symbol_rate * samples_per_symbol;   % 8 MS/s

channel_index = 0;
centre_hz = 2.402e9;

num_packets = 20;
payload_bytes = 27;

idle_s = 200e-6;
idle_samples = round(idle_s * fs);

snrs = [Inf 30 20 15 10 5 0 -5 -10];

% Reproducible payloads + noise
rng(42);

fprintf('Bluetooth Classic %s\n', phy);
fprintf('  symbol rate: %.1f Msym/s\n', symbol_rate/1e6);
fprintf('  Fs:          %.1f MS/s\n', fs/1e6);
fprintf('  SPS:         %d\n', samples_per_symbol);
fprintf('  channel:     %d\n', channel_index);

% -------------------------------------------------------------
% Bluetooth BR configuration
% -------------------------------------------------------------

cfg = bluetoothWaveformConfig( ...
    "Mode", "BR", ...
    "PacketType", "DH1", ...
    "SamplesPerSymbol", samples_per_symbol);

cfg.PayloadLength = payload_bytes;
cfg.ModulationIndex = 0.32;
cfg.WhitenStatus = "On";

% -------------------------------------------------------------
% Generate clean packet train
% -------------------------------------------------------------

wf_clean = complex([]);

for p = 1:num_packets

    % New random payload for each packet
    num_bits = payload_bytes * 8;
    bits = randi([0 1], num_bits, 1);

    packet = bluetoothWaveformGenerator(bits, cfg);
    packet = packet(:);

    % Remove zero-padding around/after the generated packet so that
    % our explicit idle_s value controls the inter-packet gap.
    active_packet = find(abs(packet) > 1e-12);

    if isempty(active_packet)
        error('Generated packet %d contains no active samples.', p);
    end

    packet = packet(active_packet(1):active_packet(end));

    % Random packet carrier phase
    phi = 2*pi*rand;
    packet = packet .* exp(1j*phi);

    wf_clean = [
        wf_clean;
        packet;
        complex(zeros(idle_samples, 1))
    ];
end

% -------------------------------------------------------------
% Normalise waveform
%
% Match the LE2M generator convention.
% -------------------------------------------------------------

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

        tag = sprintf('bluetooth_br_snr%+03d', snr_db);

    else

        wf = wf_clean;
        tag = 'bluetooth_br_clean';

    end

    % ---------------------------------------------------------
    % Write interleaved float32 IQ
    % ---------------------------------------------------------

    base = fullfile(outdir, tag);

    fid = fopen([base '.bin'], 'w');

    if fid < 0
        error('Could not open %s.bin for writing.', base);
    end

    iq = [real(wf).'; imag(wf).'];
    fwrite(fid, single(iq(:)), 'float32');

    fclose(fid);

    % ---------------------------------------------------------
    % Metadata
    % ---------------------------------------------------------

    meta = fopen([base '.txt'], 'w');

    if meta < 0
        error('Could not open %s.txt for writing.', base);
    end

    fprintf(meta, 'fs_hz=%.1f\n', fs);
    fprintf(meta, 'centre_hz=%.1f\n', centre_hz);

    fprintf(meta, ...
        'expect=Bluetooth Classic BR (GFSK)\n');

    fprintf(meta, 'expected_mod=GFSK\n');
    fprintf(meta, 'source=matlab_bluetooth_toolbox\n');

    fprintf(meta, 'phy=%s\n', phy);
    fprintf(meta, 'packet_type=DH1\n');
    fprintf(meta, 'channel_index=%d\n', channel_index);

    fprintf(meta, 'symbol_rate_hz=%.1f\n', symbol_rate);
    fprintf(meta, 'samples_per_symbol=%d\n', samples_per_symbol);
    fprintf(meta, 'modulation_index=%.3f\n', cfg.ModulationIndex);

    fprintf(meta, 'snr_db=%g\n', snr_db);
    fprintf(meta, 'n_samples=%d\n', numel(wf));
    fprintf(meta, 'packets=%d\n', num_packets);
    fprintf(meta, 'payload_bytes=%d\n', payload_bytes);
    fprintf(meta, 'idle_s=%g\n', idle_s);

    fclose(meta);

    fprintf('  %-28s %d samples (%.2f ms)\n', ...
        tag, numel(wf), numel(wf)/fs*1e3);
end

fprintf('\ndone\n');