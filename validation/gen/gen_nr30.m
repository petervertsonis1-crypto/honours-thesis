% gen_nr30.m
%
% Synthetic 5G NR FR1 downlink waveform for protocol-classifier testing.
%
% Configuration:
%   - FR1
%   - 10 MHz channel
%   - 30 kHz subcarrier spacing
%   - 24 resource blocks
%   - 64-QAM PDSCH
%   - Case-B SS/PBCH burst
%   - 20 x 1 ms NR subframes
%   - 0.5 ms quiet gap after each subframe
%
% Outputs:
%   nr30_clean
%   nr30_snr+30
%   nr30_snr+20
%   nr30_snr+15
%   nr30_snr+10
%   nr30_snr+05
%   nr30_snr+00
%   nr30_snr-05
%   nr30_snr-10

clear;
clc;

outdir = gen_outdir();
fprintf('writing to %s\n', outdir);

rng(42);

% =============================================================
% Experiment parameters
% =============================================================

num_bursts = 20;

% One genuine NR subframe = 1 ms.
burst_s = 1e-3;

% Explicit silence between subframes so Philip's detector can
% separate them as bursts.
idle_s = 0.5e-3;

% Representative FR1 RF centre frequency.
% Waveform itself remains complex baseband.
centre_hz = 3.500e9;

channel_bw_mhz = 10;
scs_khz = 30;

% 10 MHz / 30 kHz NR carrier -> 24 resource blocks.
n_rb = 24;

snrs = [Inf 30 20 15 10 5 0 -5 -10];

% =============================================================
% 30 kHz SCS carrier
% =============================================================

scsCarrier = nrSCSCarrierConfig( ...
    'SubcarrierSpacing', scs_khz, ...
    'NSizeGrid', n_rb, ...
    'NStartGrid', 0);

% =============================================================
% Bandwidth part
% =============================================================

bwp = nrWavegenBWPConfig( ...
    'BandwidthPartID', 1, ...
    'SubcarrierSpacing', scs_khz, ...
    'NSizeBWP', n_rb, ...
    'NStartBWP', 0);

% =============================================================
% PDSCH
%
% Fill the complete 24-RB bandwidth part with 64-QAM.
% =============================================================

pdsch = nrWavegenPDSCHConfig( ...
    'BandwidthPartID', 1, ...
    'Modulation', '64QAM', ...
    'PRBSet', 0:(n_rb-1));

% =============================================================
% SS/PBCH burst
%
% Case B corresponds to FR1 with 30 kHz SCS.
% =============================================================

ssburst = nrWavegenSSBurstConfig;

ssburst.Enable = 1;
ssburst.Power = 0;

ssburst.BlockPattern = 'Case B';

% Four active SS blocks is sufficient and matches the usual
% FR1-style bitmap.
ssburst.TransmittedBlocks = [1 1 1 1];

ssburst.Period = 20;

% Centre the SSB automatically within the carrier.
ssburst.NCRBSSB = [];

% MIB indicates 30 kHz common SCS.
ssburst.SubcarrierSpacingCommon = 30;

% =============================================================
% CORESET
%
% MATLAB's default CORESET spans 48 RB, which caused the previous
% validation failure.
%
% Each element of FrequencyResources corresponds to 6 RB:
%
%   4 x 6 RB = 24 RB
%
% exactly matching our bandwidth part.
% =============================================================

coreset = nrCORESETConfig( ...
    'CORESETID', 1, ...
    'FrequencyResources', [1 1 1 1], ...
    'Duration', 2);

% =============================================================
% Search space
%
% Associate it with our explicitly defined 24-RB CORESET.
% =============================================================

searchSpace = nrSearchSpaceConfig( ...
    'SearchSpaceID', 1, ...
    'CORESETID', 1, ...
    'SearchSpaceType', 'ue', ...
    'StartSymbolWithinSlot', 0, ...
    'NumCandidates', [4 2 1 0 0]);

% =============================================================
% PDCCH
%
% We do not need PDCCH data for Philip's physical-layer feature
% classifier. Define it explicitly but disable it so that MATLAB
% does not instantiate an incompatible default control channel.
% =============================================================

pdcch = nrWavegenPDCCHConfig( ...
    'Enable', 0, ...
    'BandwidthPartID', 1, ...
    'SearchSpaceID', 1);

% =============================================================
% Full downlink carrier configuration
% =============================================================

cfg = nrDLCarrierConfig( ...
    'FrequencyRange', 'FR1', ...
    'ChannelBandwidth', channel_bw_mhz, ...
    'NCellID', 42, ...
    'NumSubframes', num_bursts, ...
    'SCSCarriers', {scsCarrier}, ...
    'BandwidthParts', {bwp}, ...
    'SSBurst', ssburst, ...
    'CORESET', {coreset}, ...
    'SearchSpaces', {searchSpace}, ...
    'PDCCH', {pdcch}, ...
    'PDSCH', {pdsch});

% No extra OFDM windowing.
cfg.WindowingPercent = 0;

% =============================================================
% Generate continuous NR waveform
% =============================================================

[wave_raw, info] = nrWaveformGenerator(cfg);

% Use one antenna only.
wave_raw = wave_raw(:,1);

% Obtain actual waveform parameters directly from MATLAB.
fs = info.ResourceGrids(1).Info.SampleRate;
nfft = info.ResourceGrids(1).Info.Nfft;

samples_per_subframe = round(fs * burst_s);
idle_samples = round(fs * idle_s);

fprintf('\n5G NR waveform configuration\n');
fprintf('  frequency range:     FR1\n');
fprintf('  RF centre:           %.3f GHz\n', centre_hz/1e9);
fprintf('  channel bandwidth:   %.1f MHz\n', channel_bw_mhz);
fprintf('  SCS:                 %.1f kHz\n', scs_khz);
fprintf('  resource blocks:     %d\n', n_rb);
fprintf('  PDSCH modulation:    64-QAM\n');
fprintf('  SSB pattern:         Case B\n');
fprintf('  sample rate:         %.3f MS/s\n', fs/1e6);
fprintf('  FFT size:            %d\n', nfft);
fprintf('  generated subframes: %d\n', num_bursts);
fprintf('  burst duration:      %.3f ms\n', burst_s*1e3);
fprintf('  idle gap:            %.3f ms\n', idle_s*1e3);

% =============================================================
% Sanity check waveform length
% =============================================================

expected_samples = ...
    num_bursts * samples_per_subframe;

if numel(wave_raw) < expected_samples

    error( ...
        ['nrWaveformGenerator returned fewer samples than expected.\n' ...
         'Expected at least %d samples, received %d.'], ...
         expected_samples, ...
         numel(wave_raw));

end

% =============================================================
% Convert continuous NR waveform into isolated 1 ms bursts
% =============================================================

total_samples = ...
    num_bursts * ...
    (samples_per_subframe + idle_samples);

wf_clean = ...
    complex(zeros(total_samples,1));

active_mask = ...
    false(total_samples,1);

write_pos = 1;

for p = 1:num_bursts

    % Extract one genuine NR subframe from the continuous waveform.
    i0 = (p-1)*samples_per_subframe + 1;
    i1 = p*samples_per_subframe;

    packet = wave_raw(i0:i1);

    % Random absolute phase for each transmission.
    %
    % This preserves all OFDM/CP structure.
    packet = packet .* exp(1j*2*pi*rand);

    % Output locations.
    j0 = write_pos;
    j1 = j0 + samples_per_subframe - 1;

    wf_clean(j0:j1) = packet;
    active_mask(j0:j1) = true;

    % Leave following idle samples at zero.
    write_pos = ...
        j1 + idle_samples + 1;

end

% =============================================================
% Normalise waveform
% =============================================================

peak = max(abs(wf_clean));

if peak <= 0
    error('Generated NR waveform contains no signal.');
end

wf_clean = ...
    0.8 .* wf_clean ./ peak;

% Signal power based only on the active NR portions.
signal_power = ...
    mean(abs(wf_clean(active_mask)).^2);

fprintf('  active signal power: %.6f\n', ...
    signal_power);

fprintf('  total duration:      %.3f ms\n', ...
    numel(wf_clean)/fs*1e3);

% =============================================================
% Clean occupied-bandwidth sanity check
%
% Concatenate only active NR samples before calculating OBW.
% =============================================================

active_waveform = ...
    wf_clean(active_mask);

bw_clean = ...
    obw(active_waveform, fs);

fprintf('  MATLAB clean BW99:   %.3f MHz\n', ...
    bw_clean/1e6);

% =============================================================
% Generate SNR sweep
% =============================================================

for k = 1:numel(snrs)

    snr_db = snrs(k);

    if isfinite(snr_db)

        % Noise power relative to active NR signal power.
        noise_power = ...
            signal_power / (10^(snr_db/10));

        noise = ...
            sqrt(noise_power/2) .* ...
            ( ...
                randn(size(wf_clean)) + ...
                1j*randn(size(wf_clean)) ...
            );

        % AWGN exists across the whole observation window,
        % including the explicit quiet intervals.
        wf = wf_clean + noise;

        tag = ...
            sprintf('nr30_snr%+03d', snr_db);

    else

        wf = wf_clean;

        tag = 'nr30_clean';

    end

    base = ...
        fullfile(outdir, tag);

    % =========================================================
    % Write interleaved float32 IQ
    % =========================================================

    fid = ...
        fopen([base '.bin'], 'w');

    if fid < 0
        error( ...
            'Could not open %s.bin for writing.', ...
            base);
    end

    iq = ...
        [real(wf).'; imag(wf).'];

    fwrite( ...
        fid, ...
        single(iq(:)), ...
        'float32');

    fclose(fid);

    % =========================================================
    % Metadata
    % =========================================================

    meta = ...
        fopen([base '.txt'], 'w');

    if meta < 0
        error( ...
            'Could not open %s.txt for writing.', ...
            base);
    end

    fprintf(meta, ...
        'fs_hz=%.6f\n', ...
        fs);

    fprintf(meta, ...
        'centre_hz=%.1f\n', ...
        centre_hz);

    fprintf(meta, ...
        'expect=5G NR (OFDM, 30 kHz SCS)\n');

    fprintf(meta, ...
        'expected_mod=OFDM\n');

    fprintf(meta, ...
        'source=matlab_5g_toolbox\n');

    fprintf(meta, ...
        'protocol=5G_NR\n');

    fprintf(meta, ...
        'direction=downlink\n');

    fprintf(meta, ...
        'frequency_range=FR1\n');

    fprintf(meta, ...
        'channel_bw_hz=%.1f\n', ...
        channel_bw_mhz*1e6);

    fprintf(meta, ...
        'scs_hz=%.1f\n', ...
        scs_khz*1e3);

    fprintf(meta, ...
        'resource_blocks=%d\n', ...
        n_rb);

    fprintf(meta, ...
        'fft_size=%d\n', ...
        nfft);

    fprintf(meta, ...
        'modulation=64QAM\n');

    fprintf(meta, ...
        'ssb_pattern=Case_B\n');

    fprintf(meta, ...
        'snr_db=%g\n', ...
        snr_db);

    fprintf(meta, ...
        'n_samples=%d\n', ...
        numel(wf));

    fprintf(meta, ...
        'bursts=%d\n', ...
        num_bursts);

    fprintf(meta, ...
        'burst_s=%.9f\n', ...
        burst_s);

    fprintf(meta, ...
        'idle_s=%.9f\n', ...
        idle_s);

    fclose(meta);

    fprintf( ...
        '  %-20s %d samples (%.2f ms)\n', ...
        tag, ...
        numel(wf), ...
        numel(wf)/fs*1e3);

end

fprintf('\ndone\n');