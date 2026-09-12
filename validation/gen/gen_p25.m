% gen_p25.m
% Generate synthetic P25 Phase 1 C4FM PHY captures.
%
% Based on the C4FM synthesis structure used in the MathWorks
% "P25 Spectrum Sensing with Synthesized and Captured Data" example.
%
% NOTE:
% This generates the P25 Phase-1 C4FM physical-layer modulation from
% random dibits. It is not a complete encoded P25 voice/control frame.
%
% Produces:
%   p25_c4fm_clean
%   p25_c4fm_snr+30
%   p25_c4fm_snr+20
%   ...
%   p25_c4fm_snr-10

clear;
clc;

outdir = gen_outdir();
fprintf('writing to %s\n', outdir);

% -------------------------------------------------------------
% Experiment parameters
% -------------------------------------------------------------

symbol_rate = 4800;         % P25 Phase 1: 4800 symbols/s

% MathWorks synthesis structure:
% raised-cosine interpolation x4
% inverse-sinc interpolation x2
native_sps = 8;
native_fs  = symbol_rate * native_sps;   % 38.4 kHz

% Resample final waveform to a conventional narrowband IQ rate
fs = 48e3;

% Arbitrary P25-compatible RF centre.
% Also deliberately inside DMR's broad database range.
centre_hz = 851.0125e6;

num_bursts = 20;

% Keep duration inside BOTH Philip's DMR and P25 ranges:
% DMR: 20 ms - 500 ms
% P25: 20 ms - 5 s
burst_s = 50e-3;

idle_s = 20e-3;
idle_samples = round(idle_s * fs);

snrs = [Inf 30 20 15 10 5 0 -5 -10];

% P25 C4FM deviation step:
% symbols -3,-1,+1,+3 -> approximately
% -1800,-600,+600,+1800 Hz
freq_dev_step = 600;

rng(42);

fprintf('P25 Phase 1 C4FM generator\n');
fprintf('  symbol rate:     %.1f sym/s\n', symbol_rate);
fprintf('  native Fs:       %.1f kS/s\n', native_fs/1e3);
fprintf('  output Fs:       %.1f kS/s\n', fs/1e3);
fprintf('  centre:          %.4f MHz\n', centre_hz/1e6);
fprintf('  bursts:          %d\n', num_bursts);
fprintf('  burst duration:  %.1f ms\n', burst_s*1e3);
fprintf('  idle gap:        %.1f ms\n', idle_s*1e3);

% -------------------------------------------------------------
% P25 pulse-shaping filters
%
% This follows the MathWorks C4FM synthesis example:
%   four-level symbols
%       -> normal raised cosine
%       -> inverse-sinc interpolation
%       -> frequency modulation
% -------------------------------------------------------------

rctFilt = comm.RaisedCosineTransmitFilter( ...
    'Shape', 'Normal', ...
    'RolloffFactor', 0.2, ...
    'OutputSamplesPerSymbol', 4, ...
    'FilterSpanInSymbols', 60, ...
    'Gain', 1.9493);

% C4FM includes inverse-sinc compensation for the receiver's
% integrate-and-dump response.
d2 = fdesign.interpolator(2, 'Inverse-sinc Lowpass');
invSinc = design(d2, 'SystemObject', true);

% -------------------------------------------------------------
% Generate CLEAN burst train
% -------------------------------------------------------------

wf_clean = complex([]);

target_native_samples = round(burst_s * native_fs);

% Generate extra symbols around each target burst so that the section
% we keep is well away from pulse-shaping filter transients.
target_symbols = ceil(burst_s * symbol_rate);
padding_symbols = 100;
num_symbols = target_symbols + 2*padding_symbols;

for p = 1:num_bursts

    reset(rctFilt);
    reset(invSinc);

    % Random quaternary symbols 0,1,2,3
    x = randi([0 3], num_symbols, 1);

    % Map to P25 C4FM levels:
    %
    % 0 -> -3
    % 1 -> -1
    % 2 -> +1
    % 3 -> +3
    %
    % With 600 Hz/unit modulation sensitivity this produces the
    % nominal four deviation levels:
    %
    % -1800, -600, +600, +1800 Hz
    sym = 2*x - 3;

    % Raised-cosine pulse shaping
    shaped = rctFilt(sym);

    % P25 inverse-sinc compensation
    shaped = invSinc(shaped);

    shaped = shaped(:);

    % ---------------------------------------------------------
    % Remove filter startup/end transients
    % ---------------------------------------------------------

    if numel(shaped) < target_native_samples
        error('Generated C4FM waveform is shorter than target burst.');
    end

    start_idx = floor((numel(shaped) - target_native_samples)/2) + 1;

    shaped = shaped( ...
        start_idx : start_idx + target_native_samples - 1);

    % ---------------------------------------------------------
    % Frequency modulation
    %
    % IMPORTANT:
    % shaped is sampled at native_fs = 38.4 kHz.
    %
    % The instantaneous frequency is approximately:
    %
    %     f[n] = 600 * shaped[n]
    %
    % giving nominal symbol levels near
    % +/-600 Hz and +/-1800 Hz.
    % ---------------------------------------------------------

    inst_freq_hz = freq_dev_step * shaped;

    phase = 2*pi*cumsum(inst_freq_hz) / native_fs;

    packet = exp(1j * phase);

    % ---------------------------------------------------------
    % Resample 38.4 kHz -> 48 kHz
    % ---------------------------------------------------------

    packet = resample(packet, 5, 4);

    % Force exact burst duration after resampling
    target_output_samples = round(burst_s * fs);

    if numel(packet) > target_output_samples
        packet = packet(1:target_output_samples);
    elseif numel(packet) < target_output_samples
        packet(end+1:target_output_samples,1) = packet(end);
    end

    % Independent carrier phase for each transmission
    phi = 2*pi*rand;
    packet = packet .* exp(1j*phi);

    % Append packet + explicit quiet interval
    wf_clean = [
        wf_clean;
        packet;
        complex(zeros(idle_samples, 1))
    ];

end

% -------------------------------------------------------------
% Normalise
% -------------------------------------------------------------

wf_clean = 0.8 * wf_clean / max(abs(wf_clean));

% Signal power from ACTIVE samples only
active = abs(wf_clean) > 1e-12;

signal_power = mean(abs(wf_clean(active)).^2);

fprintf('  active power:    %.6f\n', signal_power);
fprintf('  capture length:  %.3f s\n', numel(wf_clean)/fs);

% -------------------------------------------------------------
% Generate SNR sweep
% -------------------------------------------------------------

for k = 1:numel(snrs)

    snr_db = snrs(k);

    if isfinite(snr_db)

        % Same convention as our other synthetic datasets:
        % noise power is relative to active signal power.
        noise_power = signal_power / (10^(snr_db/10));

        noise = sqrt(noise_power/2) .* ...
            (randn(size(wf_clean)) + ...
             1j*randn(size(wf_clean)));

        wf = wf_clean + noise;

        tag = sprintf('p25_c4fm_snr%+03d', snr_db);

    else

        wf = wf_clean;
        tag = 'p25_c4fm_clean';

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
    % Metadata sidecar
    % ---------------------------------------------------------

    meta = fopen([base '.txt'], 'w');

    if meta < 0
        error('Could not open %s.txt for writing.', base);
    end

    fprintf(meta, 'fs_hz=%.1f\n', fs);
    fprintf(meta, 'centre_hz=%.1f\n', centre_hz);

    fprintf(meta, 'expect=P25 Phase 1 (C4FM)\n');
    fprintf(meta, 'expected_mod=C4FM / 4-FSK\n');
    fprintf(meta, 'source=matlab_comm_toolbox_p25_synthesis\n');

    fprintf(meta, 'protocol=P25_Phase_1\n');
    fprintf(meta, 'symbol_rate_hz=%.1f\n', symbol_rate);

    fprintf(meta, 'native_fs_hz=%.1f\n', native_fs);
    fprintf(meta, 'output_fs_hz=%.1f\n', fs);

    fprintf(meta, 'c4fm_deviation_step_hz=%.1f\n', ...
        freq_dev_step);

    fprintf(meta, 'c4fm_inner_deviation_hz=%.1f\n', ...
        freq_dev_step);

    fprintf(meta, 'c4fm_outer_deviation_hz=%.1f\n', ...
        3*freq_dev_step);

    fprintf(meta, 'snr_db=%g\n', snr_db);
    fprintf(meta, 'n_samples=%d\n', numel(wf));
    fprintf(meta, 'bursts=%d\n', num_bursts);
    fprintf(meta, 'burst_s=%g\n', burst_s);
    fprintf(meta, 'idle_s=%g\n', idle_s);

    fclose(meta);

    fprintf('  %-26s %d samples (%.3f s)\n', ...
        tag, numel(wf), numel(wf)/fs);

end

fprintf('\ndone\n');