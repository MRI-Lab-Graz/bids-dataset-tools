% Load and validate config file
config_path = 'config_physio.json';
if ~isfile(config_path)
    error('Configuration file not found: %s', config_path);
end

config_text = fileread(config_path);
config = jsondecode(config_text);

% Validate required fields
required_fields = {'puls_path', 'phys_output_dir', 'json_bold_path', 'nr_vols'};
for i = 1:length(required_fields)
    if ~isfield(config, required_fields{i})
        error('Missing field in config file: %s', required_fields{i});
    end
end

% Assign config variables
puls_path = config.puls_path;
phys_output_dir = config.phys_output_dir;
json_bold_path = config.json_bold_path;
nr_vols = config.nr_vols;


fprintf('Scanning for PULS and RESP files...\n');

% Include both .puls and .resp files
puls_files = dir(fullfile(puls_path, '*.puls'));
resp_files = dir(fullfile(puls_path, '*.resp'));
sub = [puls_files; resp_files];


fprintf('%d physio files found.\n', length(sub));

% Enable json writing-option
json.startup

% Preallocate results table
num_files = length(sub);
% Preallocate results table with correct data types
t = table('Size', [num_files, 7], 'VariableTypes', {'cell', 'cell', 'cell', 'duration', 'double', 'double', 'double'}, ...
    'VariableNames', {'Subject', 'Session', 'Modality', 'Offset', 'AvgBeats', 'TRCount', 'Written'});

for s = 1:num_files
    fprintf('_______________\n');
    fprintf('Working on %s \n', sub(s).name);
    
    % Determine modality and parameters
    [~, ~, ext] = fileparts(sub(s).name);
    if strcmp(ext, '.puls')
        physio_mod = 'PPU';
        physio_mode_desc = 'cardiac';
        physio_sample = 20; % Sample rate for XA31
    elseif strcmp(ext, '.resp')
        physio_mod = 'RESP';
        physio_mode_desc = 'respiratory';
        physio_sample = 2.5; % Sample rate for XA31
    else
        fprintf('%s is not a valid Physio File.\n', sub(s).name);
        continue;
    end
    
    params = get_modality_params(physio_mod);
    fprintf('Starting conversion of %s file: %s \n', physio_mod, sub(s).name);
    
    % Prepare output file name
    base_name = extractBefore(sub(s).name, '_recording');
    physio_out = fullfile(phys_output_dir, [base_name '_recording-' physio_mode_desc '_physio']);
    
    % Prepare JSON content
    json_phys_text = struct(...
        'SamplingFrequency', params.SampleRate, ...
        'StartTime', 0, ...
        'Columns', {params.Columns}, ...
        'Manufacturer', 'Siemens', ...
        params.Columns{1}, {{'Description', ['continuous ' physio_mod ' measurement'], 'Units', 'mV'}}, ...
        'trigger', {{'Description', 'continuous measurement of the scanner trigger signal'}});

    % Read BOLD JSON to get TR
    search_for = base_name;
    search_pattern = sprintf('%s*_bold.json', search_for);
    json_sub = dir(fullfile(json_bold_path, search_pattern));

if isempty(json_sub)
    warning('No matching BOLD JSON file found for %s. Skipping.', search_for);
    continue;
end

    % Read the first matching JSON file
    bold_json = fileread(fullfile(json_sub(1).folder, json_sub(1).name));
    val = jsondecode(bold_json);
    TR = val.RepetitionTime;
    
    curr_puls_file = fullfile(sub(s).folder, sub(s).name);
    
    fprintf('Reading physio file and extracting start time...\n');
    % Read physio file and get start time
    try
    [lineData, ~, linesFooter] = tapas_physio_read_physlogfiles_siemens_raw(curr_puls_file);
    
    % Extract LogStartMDHTime using regexp
    footerText = strjoin(linesFooter, '\n');
    tokens = regexp(footerText, 'LogStartMDHTime:\s*(\d+)', 'tokens');
        if ~isempty(tokens)
        LogTimeStart = str2double(tokens{1}{1});
    else
        error('LogStartMDHTime not found in footer.');
    end
    catch
     continue
    end

    
    % Read in PPU data
    ppuData = gpt_physio_siemens_line2table(lineData, physio_mod);
    
    % Vectorized time calculation
    num_samples = size(ppuData, 1);
    ppuData(:,4) = LogTimeStart + params.PhysioSample * (0:num_samples-1)';
    
    % Write readable time
    bids_ppuData_time = seconds(ppuData(:,4)/1000);
    bids_ppuData_time.Format = 'hh:mm:ss';
    
    % Bring relevant data to new variable (data and trigger)
    bids_ppuData = [ppuData(:,1), ppuData(:,3) == 5000 ];
    
    % Find closest match between bold-onset and physio time-series
    time_fmri = timeofday(datetime(val.AcquisitionTime,'Format','HH:mm:ss.SSS'));
    diffs = abs(bids_ppuData_time - time_fmri);
    [~, idx] = min(diffs);
    
    % Compute end of bold
    diff_onset = bids_ppuData_time(idx) - bids_ppuData_time(1);
    end_fmri = bids_ppuData_time(idx) + seconds(TR*nr_vols);
    
    % Update results table
    sub_name_parts = split(sub(s).name, "_");
    t.Subject{s} = sub_name_parts{1};
    t.Session{s} = sub_name_parts{2};
    t.Modality{s} = physio_mod;
    t.Offset(s) = diff_onset;
    
    % Find end index
    diffs_end = abs(bids_ppuData_time - end_fmri);
    [~, idx_end] = min(diffs_end);
    
    % Truncate physio data
    bids_physio_trunc = bids_ppuData(idx:idx_end, :);
    
    % Count triggers and calculate average beats
    tr_count = sum(bids_physio_trunc(:,2));
    avg_beats = tr_count / (TR * nr_vols / 60);
    t.TRCount(s) = tr_count;
    t.AvgBeats(s) = avg_beats;
    
    % Write output files
    writematrix(bids_physio_trunc,[physio_out '.csv'],'Delimiter','tab');
    movefile([physio_out '.csv'], [physio_out '.tsv']);
    % Compress the .tsv file into a .gz file
    gzip([physio_out '.tsv']);

    % Optionally, delete the original .tsv file if you only need the compressed version
    delete([physio_out '.tsv']);
    t.written(s,1) = "Yes";
    %else
    
    % Write JSON file
    json.write(json_phys_text, [physio_out '.json']);
    
    t.Written(s) = 1;
    
    fprintf('Processed %s successfully.\n', sub(s).name);
end

% Save results table
filename = ['Sum_up_conversion_' datestr(now,'yyyy-mm-dd_HH_MM_SS') '.txt'];
writetable(t, filename, 'Delimiter', '\t');

% Helper function to get modality parameters
function params = get_modality_params(modality)
    switch modality
        case 'PPU'
            params.SampleRate = 50.0;
            params.PhysioSample = 20;
            params.Columns = {'cardiac', 'trigger'};
        case 'RESP'
            params.SampleRate = 400.0;
            params.PhysioSample = 2.5;
            params.Columns = {'respiratory', 'trigger'};
        otherwise
            error('Unknown modality: %s', modality);
    end
end
