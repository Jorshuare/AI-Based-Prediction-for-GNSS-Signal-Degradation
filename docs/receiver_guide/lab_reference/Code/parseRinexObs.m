clc; clear; close all;

filename = 'GSEPT0760.25O';

fid = fopen(filename, 'r');
if fid == -1
    error('Failed to open file：%s', filename);
end

header = struct();
header.comments = {};
header.obsTypes = struct();

obsData = struct('GPS', [], 'GLONASS', [], 'Galileo', [], 'BDS', [], 'QZSS', [], 'SBAS', []);

% --- Read header ---
headerLines = {};
while true
    line = fgetl(fid);
    headerLines{end+1} = line;
    if contains(line, 'END OF HEADER')
        break;
    end
end
header.raw = headerLines;
% Extract RINEX version from the first line (characters 1-9)
header.version = str2double(strtrim(headerLines{1}(1:9)));
% 示例：Parse observation types for each system 
obsTypes = struct();
for i = 1:length(headerLines)
    if contains(headerLines{i}, 'SYS / # / OBS TYPES')
        sysID = strtrim(headerLines{i}(1));
        numObs = str2double(headerLines{i}(4:6));
        typeStr = headerLines{i}(8:8+numObs*4-1);
        obsList = cellstr(reshape(typeStr, 4, [])');
        obsTypes.(sysID) = strtrim(obsList);
    end
end
header.obsTypes = obsTypes;


%% Read observation data
recordIndex = struct('GPS', 0, 'GLONASS', 0, 'Galileo', 0, 'BDS', 0, 'QZSS', 0, 'SBAS', 0);

while ~feof(fid)
    line = fgetl(fid);
    if ~ischar(line) || isempty(strtrim(line))
        break;
    end
    
    % Read epoch label  
    if line(1) == '>'
        epochTime = sscanf(line(2:29), '%f');
        epochFlag = str2double(line(30:32));
        if epochFlag == 1
            breakl
        end
        numSat = str2double(line(33:35));
                
        for i = 1:numSat
            line = fgetl(fid);
            if isempty(line) || ~ischar(line)
                break;
            end
            
            % Get satellite ID (G, R, E, C, J, S) 
            prn = strtrim(line(1:3));
            system = prn(1);
            switch system
                case 'G', systemName = 'GPS'; 
                case 'R', systemName = 'GLONASS';
                case 'E', systemName = 'Galileo'; 
                case 'C', systemName = 'BDS';
                case 'J', systemName = 'QZSS';
                case 'S', systemName = 'SBAS';
                otherwise, continue;
            end
            numObsTypes = size(getfield(header.obsTypes, system),1);
            formatSpec = repmat('%16c', 1, numObsTypes);
            recordIndex.(systemName) = recordIndex.(systemName) + 1;
            idx = recordIndex.(systemName);
            
            obsData.(systemName)(idx).PRN = prn;
            obsData.(systemName)(idx).epoch = epochTime;
            
            % Read measurements  
            values = '';
            measNum = (length(line) -3) / 16;
            for i = 1:measNum
                startIdx = (i - 1) * 16 + 4; % 
                endIdx = startIdx + 16 - 1;
                values(i, :) = line(startIdx:endIdx);
            end

            
            % Save measurements under corresponding observation types  
            obsTypes = header.obsTypes.(system);
            for k = 1:measNum
                if k <= length(obsTypes)
                    fieldName = obsTypes{k};
                    obsData.(systemName)(idx).(fieldName) = strtrim(values(k,:));
                end
            end
        end
    end
end

fclose(fid);
obsData