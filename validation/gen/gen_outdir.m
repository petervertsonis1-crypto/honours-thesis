function outdir = gen_outdir()
%GEN_OUTDIR Output directory for generated thesis captures on external SSD.

ssd_root = '/Volumes/MySSD';

% Fail clearly if the SSD is not mounted.
if ~isfolder(ssd_root)
    error('MySSD is not mounted. Connect the SSD before generating captures.');
end

outdir = fullfile(ssd_root, 'honours-thesis', 'generated-captures');

if ~isfolder(outdir)
    mkdir(outdir);
end

end