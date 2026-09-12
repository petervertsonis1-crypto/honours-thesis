% gen_bluetooth.m
% Generate synthetic Bluetooth LE 1M captures for protocol-ID validation.

outdir = gen_outdir();
fprintf('writing to %s\n', outdir);

% Start reasonably small. We can extend this once the pipeline works.
snrs = [Inf 30 20 15 10 5 0 -5 -10];

phy = "LE1M";
sps = 8;
symbol_rate = 1e6;
fs = sps * symbol_rate;

channel_index = 37;       % BLE advertising channel
centre_hz = 2.402e9;

num_packets = 20;
idle_s = 200e-6;
idle_samples = round(idle_s * fs);

% 256 information bits + the preamble/access-address fields that
% bleWaveformGenerator adds gives us a roughly 300 us packet.
num_message_bits = 256;

fprintf('BLE %s: %.1f MS/s, channel %d\n', ...
    phy, fs/1e6, channel_index);

for k = 1:numel(snrs)
    snr = snrs(k);

    % -------------------------------------------------------------
    % 1. Generate a clean train of BLE packets
    % -------------------------------------------------------------
    wf = complex([]);

    for p = 1:num_packets
        message = randi([0 1], num_message_bits, 1);

        packet = bleWaveformGenerator(message, ...
            'Mode', phy, ...
            'SamplesPerSymbol', sps, ...
            'ChannelIndex', channel_index, ...
            'WhitenStatus', 'On');

        wf = [wf; packet; complex(zeros(idle_samples, 1))];
    end

    % -------------------------------------------------------------
    % 2. Normalise clean signal
    % -------------------------------------------------------------
    active = abs(wf) > 1e-12;

    wf = 0.8 * wf / max(abs(wf));

    % -------------------------------------------------------------
    % 3. Add controlled AWGN
    %
    % Measure power only during active packet samples. This avoids
    % the idle gaps artificially lowering the measured signal power.
    % -------------------------------------------------------------
    if isfinite(snr)
        signal_power = mean(abs(wf(active)).^2);
        noise_power = signal_power / (10^(snr / 10));

        noise = sqrt(noise_power / 2) .* ...
            (randn(size(wf)) + 1j * randn(size(wf)));

        wf = wf + noise;

        tag = sprintf('snr%+03d', snr);
    else
        tag = 'clean';
    end

    % -------------------------------------------------------------
    % 4. Write interleaved float32 IQ
    % -------------------------------------------------------------
    base = fullfile(outdir, ...
        sprintf('bluetooth_le1m_%s', tag));

    fid = fopen([base '.bin'], 'w');

    iq = [real(wf).'; imag(wf).'];
    fwrite(fid, single(iq(:)), 'float32');

    fclose(fid);

    % -------------------------------------------------------------
    % 5. Metadata
    % -------------------------------------------------------------
    meta = fopen([base '.txt'], 'w');

    fprintf(meta, 'fs_hz=%.1f\n', fs);
    fprintf(meta, 'centre_hz=%.1f\n', centre_hz);
    fprintf(meta, 'expect=Bluetooth LE 1M (GFSK)\n');
    fprintf(meta, 'expected_mod=GFSK\n');
    fprintf(meta, 'source=matlab_bluetooth_toolbox\n');
    fprintf(meta, 'phy=%s\n', phy);
    fprintf(meta, 'channel_index=%d\n', channel_index);
    fprintf(meta, 'snr_db=%g\n', snr);
    fprintf(meta, 'n_samples=%d\n', numel(wf));
    fprintf(meta, 'packets=%d\n', num_packets);
    fprintf(meta, 'idle_s=%g\n', idle_s);

    fclose(meta);

    fprintf('  %-8s %d samples (%.2f ms)\n', ...
        tag, numel(wf), numel(wf)/fs*1e3);
end

fprintf('done\n');