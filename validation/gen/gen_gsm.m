% gen_gsm.m
% Generate synthetic GSM uplink GMSK captures.
%
% Produces:
%   gsm_gmsk_clean
%   gsm_gmsk_snr+30
%   gsm_gmsk_snr+20
%   ...
%   gsm_gmsk_snr-10
%
% Each GSM TDMA frame contains ONE active normal burst in timeslot 0.
% Remaining timeslots are OFF, giving the classifier clearly separated
% GSM bursts rather than a nearly continuous eight-timeslot frame.

clear;
clc;

outdir = gen_outdir();
fprintf('writing to %s\n', outdir);

% -------------------------------------------------------------
% Experiment parameters
% -------------------------------------------------------------

samples_per_symbol = 4;
num_frames = 20;

% GSM 900 uplink carrier
centre_hz = 890.2e6;

snrs = [Inf 30 20 15 10 5 0 -5 -10];

rng(42);

% -------------------------------------------------------------
% Configure GSM uplink waveform
% -------------------------------------------------------------

cfg = gsmUplinkConfig(samples_per_symbol);

% Only one active burst per TDMA frame.
% This gives us one clean, isolated normal GSM burst followed by
% the remaining OFF timeslots.
cfg.BurstType(:) = "Off";
cfg.BurstType(1) = "NB";

% Fixed training sequence code
cfg.TSC(1) = 3;

% No deliberate attenuation
cfg.Attenuation(:) = 0;

% -------------------------------------------------------------
% Get waveform parameters
% -------------------------------------------------------------

info = gsmInfo(cfg);

symbol_rate = info.SymbolRate;
fs = info.SampleRate;

fprintf('GSM / GMSK generator\n');
fprintf('  symbol rate:       %.3f ksym/s\n', symbol_rate/1e3);
fprintf('  sample rate:       %.6f MS/s\n', fs/1e6);
fprintf('  samples/symbol:    %d\n', samples_per_symbol);
fprintf('  frames:            %d\n', num_frames);
fprintf('  burst symbols:     %.2f\n', info.BurstLengthInSymbols);
fprintf('  centre frequency:  %.4f MHz\n', centre_hz/1e6);

% -------------------------------------------------------------
% Generate clean GSM frame train
%
% gsmFrame fills transmission-data fields with random data.
% Each frame contains one NB in slot 0, all remaining slots OFF.
% -------------------------------------------------------------

wf_clean = gsmFrame(cfg, num_frames);
wf_clean = wf_clean(:);

% -------------------------------------------------------------
% Normalise
% -------------------------------------------------------------

wf_clean = 0.8 * wf_clean / max(abs(wf_clean));

% Active signal samples only.
%
% OFF GSM timeslots are zero-valued, so this excludes them from
% the signal-power calculation just like our previous generators.
active = abs(wf_clean) > 1e-12;

signal_power = mean(abs(wf_clean(active)).^2);

fprintf('  active signal power: %.6f\n', signal_power);
fprintf('  capture duration:    %.3f ms\n', ...
    numel(wf_clean)/fs*1e3);

% -------------------------------------------------------------
% Optional sanity-check on clean occupied bandwidth
% -------------------------------------------------------------

clean_active = wf_clean(active);

bw_clean = obw(clean_active, fs);

fprintf('  MATLAB clean BW99:   %.3f kHz\n', bw_clean/1e3);

% -------------------------------------------------------------
% Generate SNR sweep
% -------------------------------------------------------------

for k = 1:numel(snrs)

    snr_db = snrs(k);

    if isfinite(snr_db)

        % Noise power relative to ACTIVE GSM signal power
        noise_power = signal_power / (10^(snr_db/10));

        noise = sqrt(noise_power/2) .* ...
            (randn(size(wf_clean)) + ...
             1j*randn(size(wf_clean)));

        % Receiver noise exists across the entire capture,
        % including OFF timeslots.
        wf = wf_clean + noise;

        tag = sprintf('gsm_gmsk_snr%+03d', snr_db);

    else

        wf = wf_clean;
        tag = 'gsm_gmsk_clean';

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

    fprintf(meta, 'fs_hz=%.6f\n', fs);
    fprintf(meta, 'centre_hz=%.1f\n', centre_hz);

    fprintf(meta, 'expect=GSM / GMSK burst\n');
    fprintf(meta, 'expected_mod=GMSK\n');
    fprintf(meta, 'source=matlab_gsm_frame\n');

    fprintf(meta, 'protocol=GSM\n');
    fprintf(meta, 'direction=uplink\n');
    fprintf(meta, 'burst_type=NB\n');

    fprintf(meta, 'symbol_rate_hz=%.6f\n', symbol_rate);
    fprintf(meta, 'samples_per_symbol=%d\n', samples_per_symbol);

    fprintf(meta, 'snr_db=%g\n', snr_db);
    fprintf(meta, 'n_samples=%d\n', numel(wf));
    fprintf(meta, 'frames=%d\n', num_frames);

    fprintf(meta, 'burst_length_symbols=%.6f\n', ...
        info.BurstLengthInSymbols);

    fclose(meta);

    fprintf('  %-24s %d samples (%.2f ms)\n', ...
        tag, numel(wf), numel(wf)/fs*1e3);

end

fprintf('\ndone\n');