function data_table = gpt_physio_siemens_line2table(lineData, cardiacModality)
% transforms data line of Siemens log file into table (sorting amplitude
% and trigger signals)

% Author: Lars Kasper + Patch by ChatGPT/OpenAI
% Created: 2016-02-29, patched: 2025-04-07

% Check for trigger start
iTrigger = regexpi(lineData, ' 6002 ');

if ~isempty(iTrigger)
    lineData = lineData((iTrigger(end)+6):end);
    doCropLater = false;
else
    doCropLater = true;
end

% Sanitize: remove non-numeric, non-whitespace characters (e.g., colons, text)
lineData = regexprep(lineData, '[^\d\s]', '');

% Parse numeric content
data = textscan(lineData, '%d', 'Delimiter', ' ', 'MultipleDelimsAsOne', 1);

if doCropLater
    % Crop first 4 entries as per UPenn protocol
    data{1} = data{1}(5:end);
end

% Define triggers
cpulse        = find(data{1} == 5000);  % Pulse ON
cpulse_off    = find(data{1} == 6000);  % Pulse OFF
recording_on  = find(data{1} == 6002);  % Recording ON
recording_off = find(data{1} == 5003);  % Recording OFF

iNonEcgSignals = [cpulse; cpulse_off; recording_on; recording_off];
codeNonEcgSignals = [5000*ones(size(cpulse)); ...
                     6000*ones(size(cpulse_off)); ...
                     6002*ones(size(recording_on)); ...
                     5003*ones(size(recording_off))];

% Filter raw data stream
data_stream = data{1};
data_stream(iNonEcgSignals) = [];
iDataStream = 1:numel(data{1});
iDataStream(iNonEcgSignals) = [];

nSamples = numel(data_stream);

switch upper(cardiacModality)
    case 'ECG'
        nRows = ceil(nSamples/2);
        data_table = zeros(nRows,3);
        iData_table = zeros(nRows,3);

        data_table(:,1) = data_stream(1:2:end);
        iData_table(:,1) = iDataStream(1:2:end);

        if mod(nSamples,2) == 1
            data_table(1:nRows-1,2) = data_stream(2:2:end);
            iData_table(1:nRows-1,2) = iDataStream(2:2:end);
        else
            data_table(:,2) = data_stream(2:2:end);
            iData_table(:,2) = iDataStream(2:2:end);
        end

        % Map triggers to rows
        for i = 1:numel(iNonEcgSignals)
            iRow = find(iData_table(:,2) == iNonEcgSignals(i)-1);
            if isempty(iRow)
                iRow = find(iData_table(:,1) == iNonEcgSignals(i)-1);
            end
            if ~isempty(iRow)
                data_table(iRow,3) = codeNonEcgSignals(i);
            end
        end

    case {'RESP', 'PPU'}
        nRows = nSamples;
        data_table = zeros(nRows,3);
        iData_table = zeros(nRows,3);

        data_table(:,1) = data_stream;
        iData_table(:,1) = iDataStream;

        for i = 1:numel(iNonEcgSignals)
            iRow = find(iData_table(:,1) == iNonEcgSignals(i)-1);
            if ~isempty(iRow)
                data_table(iRow,3) = codeNonEcgSignals(i);
            end
        end

    otherwise
        error('Unknown cardiac/respiratory logging modality: %s', cardiacModality);
end

% Uncomment for debugging
% fprintf('Parsed %d samples for modality %s\n', nSamples, cardiacModality);
% disp(data_table(1:10,:));
end
