function parsedData = parseNMEA(filename)
    % 打开文件
    fid = fopen(filename, 'r');
    if fid == -1
        error('无法打开文件: %s', filename);
    end

    % 初始化结构体数组用于保存不同类型的数据
    GGA_data = struct([]);  % GGA语句数据列表
    RMC_data = struct([]);  % RMC语句数据列表
    GSV_data = struct([]);  % GSV语句数据列表

    % 逐行读取文件内容
    while ~feof(fid)
        line = fgetl(fid);
        if ~ischar(line)
            break;  % 读取到文件末尾
        end
        if isempty(line)
            continue;  % 跳过空行
        end
        if line(1) ~= '$'
            continue;  % 非NMEA语句格式的行跳过
        end

        % 去掉开头的'$'以及结尾的校验部分'*..'
        starIdx = find(line == '*', 1);
        if ~isempty(starIdx)
            content = line(2:starIdx-1);
        else
            content = line(2:end);
        end

        % 按逗号分割字段
        parts = strsplit(content, ',');
        if isempty(parts)
            continue;
        end

        % 获取语句类型标识（例如GGA、RMC、GSV等）
        sentenceType = parts{1};  
        % 通常前两位是发话器ID（如GP），后面是语句类型
        if length(sentenceType) > 2
            typeID = sentenceType(3:end);
        else
            typeID = sentenceType;
        end

        switch upper(typeID)
            case 'GGA'  % Global Positioning System Fix Data (定位信息)
                if length(parts) >= 14
                    entry.Time         = parts{2};                        % UTC时间 (hhmmss.ss)
                    entry.Latitude     = parts{3};                        % 纬度 (ddmm.mmmm)
                    entry.LatDirection = parts{4};                        % 纬度半球 (N或S)
                    entry.Longitude    = parts{5};                        % 经度 (dddmm.mmmm)
                    entry.LonDirection = parts{6};                        % 经度半球 (E或W)
                    entry.Quality      = str2double(parts{7});            % 定位质量 (0=无定位，1=GPS，2=DGPS...)
                    entry.NumSatellites= str2double(parts{8});            % 使用卫星数
                    entry.HDOP         = str2double(parts{9});            % 水平精度因子
                    entry.Altitude     = str2double(parts{10});           % 天线高度
                    entry.AltUnit      = parts{11};                       % 高度单位
                    entry.GeoidalSep   = str2double(parts{12});           % 大地水准面高度
                    entry.GeoidalSepUnit = parts{13};                     % 大地水准面高度单位
                    % 差分GPS信息（可能为空）
                    if length(parts) >= 15
                        entry.DGPS_Age = parts{14};                       % 差分时间(秒)
                    else
                        entry.DGPS_Age = '';
                    end
                    if length(parts) >= 16
                        entry.DGPS_StationID = parts{15};                 % 差分站ID
                    else
                        entry.DGPS_StationID = '';
                    end
                    % 将此条记录添加到GGA数据列表
                    GGA_data(end+1) = entry;
                end

            case 'RMC'  % Recommended Minimum Navigation Information (推荐最小导航信息)
                if length(parts) >= 10
                    entry.Time      = parts{2};                           % UTC时间 (hhmmss.ss)
                    entry.Status    = parts{3};                           % 定位状态 (A=有效，V=无效)
                    entry.Latitude  = parts{4};                           % 纬度 (ddmm.mmmm)
                    entry.LatDirection = parts{5};                        % 纬度半球 (N或S)
                    entry.Longitude = parts{6};                           % 经度 (dddmm.mmmm)
                    entry.LonDirection = parts{7};                        % 经度半球 (E或W)
                    entry.SpeedKnots = str2double(parts{8});              % 地面速率 (节，knots)
                    entry.Course    = str2double(parts{9});               % 地面航向 (度)
                    entry.Date      = parts{10};                          % 日期 (DDMMYY)
                    % 磁偏角和方向（可能为空）
                    entry.MagVar    = [];                                 % 磁偏角大小
                    entry.MagVarDir = [];                                 % 磁偏角方向 (E/W)
                    if length(parts) >= 11 && ~isempty(strtrim(parts{11}))
                        entry.MagVar = str2double(parts{11});
                    end
                    if length(parts) >= 12 && ~isempty(parts{12})
                        entry.MagVarDir = parts{12};
                    end
                    % 某些RMC语句可能有额外的模式字段
                    if length(parts) >= 13
                        entry.Mode = parts{13};
                    end
                    % 添加到RMC数据列表
                    RMC_data(end+1) = entry;
                end

            case 'GSV'  % Satellites in View (可见卫星信息)
                if length(parts) >= 4
                    entry.TotalMessages = str2double(parts{2});           % 此次卫星信息总的语句数
                    entry.MessageNumber = str2double(parts{3});           % 本条语句是第几条
                    entry.SatsInView   = str2double(parts{4});            % 可见卫星总数
                    % 卫星信息列表初始化
                    entry.Satellites = [];  
                    % 按每4个字段解析卫星信息 (卫星ID, 仰角, 方位角, 信噪比)
                    satCountLine = floor((length(parts) - 4) / 4);
                    satList = struct([]);
                    for s = 1:satCountLine
                        baseIdx = 4 + (s-1)*4;
                        sat.ID   = str2double(parts{baseIdx + 1});        % 卫星PRN号
                        sat.Elev = str2double(parts{baseIdx + 2});        % 仰角 (度)
                        sat.Azim = str2double(parts{baseIdx + 3});        % 方位角 (度)
                        % 信噪比 SNR 可能为空（用空字符串或空格表示）
                        snrStr = strtrim(parts{baseIdx + 4});
                        if ~isempty(snrStr)
                            sat.SNR = str2double(snrStr);                 % 信噪比 (dBHz)
                        else
                            sat.SNR = NaN;                                % 若无信噪比则记为NaN
                        end
                        satList(end+1) = sat;
                    end
                    entry.Satellites = satList;
                    % 添加到GSV数据列表
                    GSV_data(end+1) = entry;
                end

            otherwise
                % 可在这里添加其他语句类型的解析，如GSA, GLL, VTG等
                % 未识别的类型暂不处理
        end
    end

    fclose(fid);

    % 将各类型数据存入输出结构体
    parsedData.GGA = GGA_data;
    parsedData.RMC = RMC_data;
    parsedData.GSV = GSV_data;
end
