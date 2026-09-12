% gen_bluetooth_fs_sweep.m
% Test whether BW99 of noisy BLE depends on receiver sample rate.

outdir = gen_outdir();
fprintf('writing to %s\n', outdir);

% -------------------------------------------------------------
% Experiment parameters
% -------------------------------------------------------------
sps_list = [4 8 12 16 20];

symbol_rate = 1e6;       % LE1M
phy = "LE1M";

channel_index = 37;
centre_hz = 2.402e9;

num_packets = 20;
num_message_bits = 256;
idle_s = 200e-6;

target_snr_db = 10;

% -------------------------------------------------------------
% Generate payloads ONCE.
% Every sample-rate experiment therefore contains the same bits.
% -------------------------------------------------------------
rng(42);
messages = randi([0 1], num_message_bits, num_packets);

for sps = sps_list

    fs = sps * symbol_rate;
    idle_samples = round(idle_s * fs);

    fprintf('\nFs = %.1f MS/s (%d samples/symbol)\n', ...
        fs/1e6, sps);

    % ---------------------------------------------------------
    % Generate clean BLE packet train
    % ---------------------------------------------------------
    wf_clean = complex([]);

    for p = 1:num_packets

        packet = bleWaveformGenerator(messages(:, p), ...
            'Mode', phy, ...
            'SamplesPerSymbol', sps, ...
            'ChannelIndex', channel_index, ...
            'WhitenStatus', 'On');

        wf_clean = [
            wf_clean;
            packet;
            complex(zeros(idle_samples, 1))
        ];
    end

    % Normalise identically at every sample rate
    wf_clean = 0.8 * wf_clean / max(abs(wf_clean));

    active = abs(wf_clean) > 1e-12;

    % ---------------------------------------------------------
    % CLEAN CAPTURE
    % ---------------------------------------------------------
    tag = sprintf('bluetooth_le1m_fs%02dm_clean', round(fs/1e6));

    write_capture( ...
        outdir, tag, wf_clean, fs, centre_hz, ...
        phy, channel_index, Inf, num_packets, idle_s);

    fprintf('  %-32s %d samples\n', tag, numel(wf_clean));

    % ---------------------------------------------------------
    % +10 dB CAPTURE
    % ---------------------------------------------------------
    signal_power = mean(abs(wf_clean(active)).^2);

    noise_power = signal_power / (10^(target_snr_db / 10));

    noise = sqrt(noise_power / 2) .* ...
        (randn(size(wf_clean)) + 1j * randn(size(wf_clean)));

    wf_noisy = wf_clean + noise;

    tag = sprintf( ...
        'bluetooth_le1m_fs%02dm_snr+10', ...
        round(fs/1e6));

    write_capture( ...
        outdir, tag, wf_noisy, fs, centre_hz, ...
        phy, channel_index, target_snr_db, ...
        num_packets, idle_s);

    fprintf('  %-32s %d samples\n', tag, numel(wf_noisy));
end

fprintf('\ndone\n');


% =================================================================
% Helper: write IQ + metadata
% =================================================================
function write_capture( ...
    outdir, tag, wf, fs, centre_hz, ...
    phy, channel_index, snr_db, num_packets, idle_s)

    base = fullfile(outdir, tag);

    % Interleaved float32 IQ
    fid = fopen([base '.bin'], 'w');

    iq = [real(wf).'; imag(wf).'];
    fwrite(fid, single(iq(:)), 'float32');

    fclose(fid);

    % Metadata
    meta = fopen([base '.txt'], 'w');

    fprintf(meta, 'fs_hz=%.1f\n', fs);
    fprintf(meta, 'centre_hz=%.1f\n', centre_hz);
    fprintf(meta, 'expect=Bluetooth LE 1M (GFSK)\n');
    fprintf(meta, 'expected_mod=GFSK\n');
    fprintf(meta, 'source=matlab_bluetooth_toolbox\n');
    fprintf(meta, 'phy=%s\n', phy);
    fprintf(meta, 'channel_index=%d\n', channel_index);
    fprintf(meta, 'snr_db=%g\n', snr_db);
    fprintf(meta, 'n_samples=%d\n', numel(wf));
    fprintf(meta, 'packets=%d\n', num_packets);
    fprintf(meta, 'idle_s=%g\n', idle_s);

    fclose(meta);
end