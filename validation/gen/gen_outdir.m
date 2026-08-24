function outdir = gen_outdir()
%GEN_OUTDIR Absolute path to thesis/captures/generated, independent of pwd.
here   = fileparts(mfilename('fullpath'));
repo   = fileparts(fileparts(here));
outdir = fullfile(repo, 'captures', 'generated');
if ~exist(outdir, 'dir'); mkdir(outdir); end
end