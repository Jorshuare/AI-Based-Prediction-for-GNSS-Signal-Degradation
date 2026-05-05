clc; clear; close all;

filename = 'GSEPT0760.25N';
fid = fopen(filename, 'r');
if fid == -1
    error('Failed to open file：%s', filename);
end

%% Read header information
headerLines = {};
while true
    line = fgetl(fid);
    if contains(line, 'END OF HEADER')
        break;
    end
    headerLines{end+1} = line;
end
header.raw = headerLines;

% Parse RINEX version and file type
header.version = str2double(strtrim(headerLines{1}(1:9)));
header.fileType = strtrim(headerLines{1}(21));

%% Read navigation data
navData = struct([]);
recordIndex = 0;

while ~feof(fid)
    % Line 1: Satellite ID + Epoch time + Clock bias information
    line = fgetl(fid);
    if ~ischar(line) || isempty(strtrim(line))
        break;
    end
    
    % Satellite ID (first 3 characters, e.g., 'G10')  
    satID = strtrim(line(1:3));
    
    % Epoch time (characters 4-22)  
    epoch = sscanf(line(4:23), '%f')';   % 年、月、日、时、分、秒
    
    %  Clock bias, drift, drift rate (19 characters each)  
    clockBias = str2double(line(24:42));
    clockDrift = str2double(line(43:61));
    clockDriftRate = str2double(line(62:80));
    
    %  Initialize record 
    recordIndex = recordIndex + 1;
    navData(recordIndex).satID = satID;
    navData(recordIndex).epoch = epoch;
    navData(recordIndex).clockBias = clockBias;
    navData(recordIndex).clockDrift = clockDrift;
    navData(recordIndex).clockDriftRate = clockDriftRate;
    
    % Read next 7 lines of orbital parameters  
    params = zeros(7, 4); % Up to 4 orbital parameters per line  
    for i = 1:7
        line = fgetl(fid);
        if length(line) >= 79
             % Each parameter spans 19 characters; handle negative signs and scientific notation
            params(i, 1) = str2double(line(4:23));
            params(i, 2) = str2double(line(24:42));
            params(i, 3) = str2double(line(43:61));
            params(i, 4) = str2double(line(62:80));
        else
            params(i, 1) = str2double(line(4:23));
            params(i, 2) = str2double(line(24:42));
        end
    end
    
    paramsVector = params';
    % Store orbital parameters
    navData(recordIndex).IODE = paramsVector(1);                           % Unitless
    navData(recordIndex).Crs_m = paramsVector(2);                          % Unit: meters
    navData(recordIndex).Delta_n_rad_per_sec = paramsVector(3);            % Unit: rad/s
    navData(recordIndex).M0_rad = paramsVector(4);                         % Unit: radians
    % Line 3
    navData(recordIndex).Cuc_rad = paramsVector(5);                        % Unit: radians
    navData(recordIndex).e = paramsVector(6);                              % Unitless
    navData(recordIndex).Cus_rad = paramsVector(7);                        % Unit: radians
    navData(recordIndex).sqrtA_sqrtm = paramsVector(8);                    % Unit: √m
    % Line 4
    navData(recordIndex).Toe_sec = paramsVector(9);                        % Unit: seconds
    navData(recordIndex).Cic_rad = paramsVector(10);                       % Unit: radians
    navData(recordIndex).Omega0_rad = paramsVector(11);                    % Unit: radians
    navData(recordIndex).Cis_rad = paramsVector(12);                       % Unit: radians
    % Line 5
    navData(recordIndex).i0_rad = paramsVector(13);                        % Unit: radians
    navData(recordIndex).Crc_m = paramsVector(14);                         % Unit: meters
    navData(recordIndex).omega_rad = paramsVector(15);                     % Unit: radians
    navData(recordIndex).OmegaDot_rad_per_sec = paramsVector(16);          % Unit: rad/s
    % Line 6
    navData(recordIndex).IDOT_rad_per_sec = paramsVector(17);              % Unit: rad/s
    navData(recordIndex).Codes = paramsVector(18);                         % Unitless (integer)
    navData(recordIndex).GPS_Week_week = paramsVector(19);                 % Unit: week
    navData(recordIndex).L2P_Flag = paramsVector(20);                      % Unitless
    % Line 7
    navData(recordIndex).SvAcc_m = paramsVector(21);                       % Unit: meters
    navData(recordIndex).SvHealth = paramsVector(22);                      % Unitless
    navData(recordIndex).TGD_sec = paramsVector(23);                       % Unit: seconds
    navData(recordIndex).IODC = paramsVector(24);                          % Unitless
    % Line 8
    navData(recordIndex).TransmissionTime_sec = paramsVector(25);          % Unit: seconds
    navData(recordIndex).FitInterval_sec = paramsVector(26);               % Unit: seconds
end

fclose(fid);

navData