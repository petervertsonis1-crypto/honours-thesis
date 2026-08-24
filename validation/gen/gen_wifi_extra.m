% gen_wifi_extra.m -- second batch of 802.11 waveforms for Philip's pipeline.
%
% Companion to gen_wifi.m. Same output directory, same sidecar format, same
% scaling, so wifi_to_npy.py handles both without changes.
%
%   1. 802.11b DSSS/CCK        -> tests the entry that pure noise falsely
%                                 matches 55% of the time
%   2. 802.11n 40 MHz (HT40)   -> tests 20 vs 40 MHz discrimination, where
%                                 bandwidth is the only separating term
%
% WHY 802.11b FIRST: the noise baseline showed 11 of 20 pure-noise files
% getting a confident "Wi-Fi 802.11b/g (DSSS/CCK)" at up to 0.87. We have
% never fed that entry a real DSSS signal, so we do not know whether it can
% tell signal from nothing. Two outcomes, both worth having: real 802.11b
% scores well above 0.87 (entry works, just has no floor), or it scores about
% the same (entry has never distinguished anything).
%
% SAMPLE RATE -- the reason these are not at 20 MS/s.
%
% BW99 is measured against the capture bandwidth. If a signal fills the whole
% capture, BW99 reads ~0.99 x Fs -- which is exactly what noise reads. 802.11b
% at 20 MS/s would land inside the database window (14-24 MHz) for the same
% reason noise lands there, and the test would prove nothing.
%
% At 44 MS/s (4x chip rate) the 22 MHz main lobe should give BW99 near 17 MHz
% with real guard band either side, while noise at 44 MS/s reads ~43.6 MHz and
% falls outside the window. That difference is the whole experiment.
%
% HT40 at 50 MS/s for the same reason -- native 40 MS/s would put BW99 at
% ~39.6 MHz, hard against the top of the 33-41 MHz window with no headroom.
% Subcarrier spacing is preserved under oversampling, so SCS should still read
% 312.5 kHz.

here   = fileparts(mfilename('fullpath'));   % .../thesis/validation/gen
repo   = fileparts(fileparts(here));         % .../thesis
outdir = fullfile(repo, 'captures', 'generated');
if ~exist(outdir, 'dir'); mkdir(outdir); end

fprintf('writing to %s\n', outdir);

snrs     = [Inf 30 20 15 10 5 0 -5 -10 -15];
IDLE_STR = '200e-6';        % kept as a string so the sidecar reads the same
idle_s   = 200e-6;          % way gen_wifi.m's does
NUM_PKTS = 20;              % matches gen_wifi.m. identify() thins to the 12
                            % longest bursts, so 12 is what you will see --
                            % same as the existing wifi_ht20_* set

% =====================================================================
% format table
% =====================================================================
formats = struct( ...
    'tag',        {'wifi11b', ...
                   'wifi_ht40'}, ...
    'expect',     {'Wi-Fi 802.11b/g (DSSS/CCK)', ...
                   'Wi-Fi 802.11n/ac/ax 40 MHz'}, ...
    'expect_mod', {'DSSS/CCK (11 Mbps)', ...
                   'OFDM (16-QAM)'}, ...
    'target_fs',  {44e6, ...
                   50e6} ...
);

for fi = 1:numel(formats)
    F = formats(fi);
    fprintf('\n=== %s ===\n', F.tag);

    if strcmp(F.tag, 'wifi11b')
        cfg = wlanNonHTConfig( ...
            'Modulation', 'DSSS', ...
            'DataRate',   '11Mbps', ...       % CCK
            'PSDULength', 1024);
    else
        cfg = wlanHTConfig( ...
            'ChannelBandwidth',    'CBW40', ...
            'NumTransmitAntennas', 1, ...
            'NumSpaceTimeStreams', 1, ...
            'MCS',                 3, ...     % 16-QAM, rate 1/2
            'PSDULength',          1024);
    end

    native_fs = wlanSampleRate(cfg);
    fprintf('native %.3f MS/s -> target %.1f MS/s\n', ...
            native_fs/1e6, F.target_fs/1e6);

    % NOTE -- deliberate difference from gen_wifi.m: the waveform is built
    % ONCE here, outside the SNR loop, so every SNR point is the same signal
    % with different noise. gen_wifi.m regenerates bits inside the loop, so
    % its SNR points differ in both noise AND payload. Worth considering a
    % regeneration of wifi_ht20_* the same way -- the noise baseline showed
    % how easily a single realisation misleads.
    bits = randi([0 1], cfg.PSDULength * 8, 1);
    wf0  = wlanWaveformGenerator(bits, cfg, ...
        'NumPackets', NUM_PKTS, ...
        'IdleTime',   idle_s);

    [p, q] = rat(F.target_fs / native_fs);
    if p ~= q
        wf0 = resample(wf0, p, q);
        fprintf('resampled %d/%d\n', p, q);
    end

    fprintf('%d samples, %.2f ms\n', numel(wf0), numel(wf0)/F.target_fs*1e3);

    for k = 1:numel(snrs)
        snr = snrs(k);

        % same scaling as gen_wifi.m: peak to 0.8 BEFORE awgn, so the SNR
        % labels mean the same thing across both scripts
        wf = 0.8 * wf0 / max(abs(wf0));

        if isfinite(snr)
            wf  = awgn(wf, snr, 'measured');
            tag = sprintf('snr%02d', snr);    % '-5' and '-10' fall out of
        else                                  % %02d without a special case
            tag = 'clean';
        end

        base = fullfile(outdir, sprintf('%s_%s', F.tag, tag));

        fid = fopen([base '.bin'], 'w');
        iq  = [real(wf).'; imag(wf).'];       % interleave I,Q,I,Q...
        fwrite(fid, single(iq(:)), 'float32');
        fclose(fid);

        meta = fopen([base '.txt'], 'w');
        fprintf(meta, 'fs_hz=%.1f\n',      F.target_fs);
        fprintf(meta, 'expect=%s\n',       F.expect);
        fprintf(meta, 'expected_mod=%s\n', F.expect_mod);
        fprintf(meta, 'snr_db=%g\n',       snr);
        fprintf(meta, 'n_samples=%d\n',    numel(wf));
        fprintf(meta, 'packets=%d\n',      NUM_PKTS);
        fprintf(meta, 'idle_s=%s\n',       IDLE_STR);
        fclose(meta);

        fprintf('  %s_%s: %d samples\n', F.tag, tag, numel(wf));
    end
end

fprintf('\ndone -- now run: python validation/tools/wifi_to_npy.py\n');