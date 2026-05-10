$(document).ready(function() {
    // 初始化地图
    var salaryChart = echarts.init(document.getElementById('salaryMap'), null, {renderer: 'canvas'});
    
    // 定义全局变量存储数据
    var mapData = [];
    var rankData = [];
    var currentMetric = 'salary'; // 默认是平均薪资
    var currentMapLevel = 'country'; // country, province, city
    var currentProvince = '';
    var currentCity = '';
    var currentDistrict = '';
    
    // 地图数据缓存
    var geoJsonData = {
        'china': null,
        'province': {},
        'city': {}
    };
    
    // 地图注册状态
    var registeredMaps = {
        'china': false
    };
    
    // 中心点数据
    var locationData = null;
    
    // 硬编码省份列表作为备用
    var hardcodedProvinces = [
        { name: '北京', adcode: '110000' },
        { name: '天津', adcode: '120000' },
        { name: '上海', adcode: '310000' },
        { name: '重庆', adcode: '500000' },
        { name: '河北', adcode: '130000' },
        { name: '山西', adcode: '140000' },
        { name: '辽宁', adcode: '210000' },
        { name: '吉林', adcode: '220000' },
        { name: '黑龙江', adcode: '230000' },
        { name: '江苏', adcode: '320000' },
        { name: '浙江', adcode: '330000' },
        { name: '安徽', adcode: '340000' },
        { name: '福建', adcode: '350000' },
        { name: '江西', adcode: '360000' },
        { name: '山东', adcode: '370000' },
        { name: '河南', adcode: '410000' },
        { name: '湖北', adcode: '420000' },
        { name: '湖南', adcode: '430000' },
        { name: '广东', adcode: '440000' },
        { name: '海南', adcode: '460000' },
        { name: '四川', adcode: '510000' },
        { name: '贵州', adcode: '520000' },
        { name: '云南', adcode: '530000' },
        { name: '陕西', adcode: '610000' },
        { name: '甘肃', adcode: '620000' },
        { name: '青海', adcode: '630000' },
        { name: '内蒙古', adcode: '150000' },
        { name: '广西', adcode: '450000' },
        { name: '西藏', adcode: '540000' },
        { name: '宁夏', adcode: '640000' },
        { name: '新疆', adcode: '650000' },
        { name: '香港', adcode: '810000' },
        { name: '澳门', adcode: '820000' },
        { name: '台湾', adcode: '710000' }
    ];
    
    // 硬编码城市-省份映射
    var cityToProvince = {
        '北京': '北京',
        '北京市': '北京',
        '上海': '上海',
        '上海市': '上海',
        '广州': '广东',
        '深圳': '广东',
        '杭州': '浙江',
        '合肥': '安徽',
        '南京': '江苏',
        '成都': '四川',
        '重庆': '重庆',
        '重庆市': '重庆',
        '武汉': '湖北',
        '长沙': '湖南',
        '西安': '陕西',
        '天津': '天津',
        '天津市': '天津',
        '苏州': '江苏',
        '宁波': '浙江',
        '青岛': '山东',
        '济南': '山东',
        '郑州': '河南',
        '石家庄': '河北',
        '福州': '福建',
        '厦门': '福建',
        '大连': '辽宁',
        '沈阳': '辽宁',
        '长春': '吉林',
        '哈尔滨': '黑龙江',
        '昆明': '云南',
        '贵阳': '贵州',
        '南宁': '广西',
        '海口': '海南',
        '银川': '宁夏',
        '西宁': '青海',
        '兰州': '甘肃',
        '太原': '山西',
        '呼和浩特': '内蒙古',
        '拉萨': '西藏',
        '乌鲁木齐': '新疆',
        '东莞': '广东',
        '佛山': '广东'
    };
    
    // 直辖市列表
    var directCities = ['北京', '上海', '天津', '重庆'];
    
    // 历史记录栈
    var historyStack = [];
    
    /**
     * 将省份简称转换为 ECharts 地图使用的全称
     * @param {string} shortName - 省份简称，例如 "广东"
     * @returns {string} - 省份全称，例如 "广东省"
     */
    function getFullProvinceName(shortName) {
        const provinceMap = {
            '北京': '北京市',
            '天津': '天津市',
            '上海': '上海市',
            '重庆': '重庆市',
            '河北': '河北省',
            '山西': '山西省',
            '辽宁': '辽宁省',
            '吉林': '吉林省',
            '黑龙江': '黑龙江省',
            '江苏': '江苏省',
            '浙江': '浙江省',
            '安徽': '安徽省',
            '福建': '福建省',
            '江西': '江西省',
            '山东': '山东省',
            '河南': '河南省',
            '湖北': '湖北省',
            '湖南': '湖南省',
            '广东': '广东省',
            '海南': '海南省',
            '四川': '四川省',
            '贵州': '贵州省',
            '云南': '云南省',
            '陕西': '陕西省',
            '甘肃': '甘肃省',
            '青海': '青海省',
            '台湾': '台湾省',
            '内蒙古': '内蒙古自治区',
            '广西': '广西壮族自治区',
            '西藏': '西藏自治区',
            '宁夏': '宁夏回族自治区',
            '新疆': '新疆维吾尔自治区',
            '香港': '香港特别行政区',
            '澳门': '澳门特别行政区'
        };
        return provinceMap[shortName] || shortName; // 如果找不到映射，则返回原名称
    }
    
    // 调试函数
    function debug(message, data) {
        console.log('[DEBUG] ' + message, data || '');
    }
    
    // 首先加载全国地图数据和中心点数据
    debug('开始加载地图数据...');
    $('#map-loading').show();
    
    // 先加载中国地图数据，不管location.json加载是否成功
    $.getJSON('/static/geojson/china.json')
        .done(function(chinaJson) {
            debug('中国地图数据加载成功');
            
            // 保存数据到缓存
            geoJsonData.china = chinaJson;
            
            // 注册全国地图
            echarts.registerMap('china', geoJsonData.china);
            registeredMaps.china = true;
            
            // 将全国地图信息推入历史记录栈
            historyStack.push({
                geoJson: geoJsonData.china,
                displayName: '全国',
                level: 'country',
                mapName: 'china',
                adcode: '100000'
            });
            
            // 尝试加载位置中心点数据
            $.getJSON('/static/geojson/location.json')
                .done(function(locationJson) {
                    debug('位置数据加载成功');
                    locationData = locationJson;
                })
                .fail(function(error) {
                    debug('位置数据加载失败，使用硬编码数据:', error);
                    // 位置数据加载失败时，使用硬编码的省份列表
                    locationData = {
                        provinceList: hardcodedProvinces,
                        cityList: []
                    };
                })
                .always(function() {
                    // 无论位置数据成功或失败，都继续初始化并加载地图数据
                    $('#map-loading').hide();
                    initProvinceSelect();
                    initEventHandlers();
                    loadMapData();
                });
        })
        .fail(function(error) {
            debug('中国地图数据加载失败:', error);
            $('#map-loading').hide();
            $('#map-error').text('地图数据加载失败，请刷新页面重试').show();
        });
    
    /**
     * 初始化省份下拉列表
     */
    function initProvinceSelect() {
        var provinceSelect = $('#province');
        provinceSelect.empty(); // 清空现有选项
        
        // 添加默认选项
        provinceSelect.append($('<option>').val('').text('全国'));
        
        // 从locationData或硬编码数据中获取省份列表
        var provincesToUse = [];
        
        if (locationData && locationData.provinceList && locationData.provinceList.length > 0) {
            debug('使用locationData中的省份列表:', locationData.provinceList.length);
            provincesToUse = locationData.provinceList;
        } else {
            debug('使用硬编码的省份列表:', hardcodedProvinces.length);
            provincesToUse = hardcodedProvinces;
        }
        
        provincesToUse.forEach(function(province) {
            provinceSelect.append($('<option>').val(province.name).text(province.name));
        });
    }
    
    /**
     * 初始化事件处理
     */
    function initEventHandlers() {
        debug('初始化事件处理程序');
        
        // 添加返回按钮到地图容器
        var $mapContainer = $('#salaryMap');
        $mapContainer.css('position', 'relative'); // 确保容器使用相对定位
        
        // 添加返回按钮元素
        var $backBtn = $('<div id="map-back-btn" class="map-control-btn" title="返回上级地图"><i class="fas fa-arrow-left"></i></div>');
        $backBtn.css({
            'position': 'absolute',
            'top': '10px',
            'left': '10px',
            'z-index': '100',
            'background': 'white',
            'border-radius': '4px',
            'box-shadow': '0 2px 6px rgba(0,0,0,0.3)',
            'padding': '5px 10px',
            'cursor': 'pointer',
            'display': 'none' // 初始状态为隐藏
        });
        $mapContainer.append($backBtn);
        
        // 添加返回按钮点击事件
        $backBtn.on('click', function() {
            debug('返回按钮点击，当前级别:', currentMapLevel, '历史栈长度:', historyStack.length);
            
            // 检查历史记录栈是否有足够的记录可以返回
            if (historyStack.length <= 1) {
                debug('历史栈中只有一条记录，无法返回上一级');
                return;
            }
            
            // 弹出当前视图
            historyStack.pop();
            
            // 获取新的栈顶，即上一级视图
            var prevMapInfo = historyStack[historyStack.length - 1];
            debug('返回到上一级:', prevMapInfo.displayName, '级别:', prevMapInfo.level);
            
            // 更新当前状态
            currentMapLevel = prevMapInfo.level;
            
            if (currentMapLevel === 'country') {
                currentProvince = '';
                currentCity = '';
                currentDistrict = '';
                $('#province').val('');
                
                // 加载全国数据
                loadMapData();
                
                // 隐藏返回按钮
                $('#map-back-btn').hide();
            } else if (currentMapLevel === 'province') {
                currentProvince = prevMapInfo.displayName;
                currentCity = '';
                currentDistrict = '';
                $('#province').val(currentProvince);
                
                // 加载省份城市数据
                loadProvinceCitiesData(currentProvince);
            } else if (currentMapLevel === 'city') {
                currentCity = prevMapInfo.displayName;
                currentDistrict = '';
                
                // 加载城市区县数据
                loadCityDistrictsData(prevMapInfo.parentName, currentCity);
            }
        });
        
        // 应用筛选按钮
        $('#applyFilter').on('click', function() {
            debug('点击应用筛选按钮');
            loadMapData();
        });
        
        // 重置按钮
        $('#resetFilter').on('click', function() {
            debug('点击重置按钮');
            $('#filterForm')[0].reset();
            resetMapLevel();
            loadMapData();
        });
        
        // 导出数据按钮
        $('#exportData').on('click', function() {
            debug('点击导出数据按钮');
            exportToCSV();
        });
        
        // 统计指标变化
        $('#metric').on('change', function() {
            debug('指标切换:', $(this).val());
            currentMetric = $(this).val();
            updateMapTitle();
            if (mapData && mapData.length > 0) {
                renderMap();
                renderRankingTable(); // 同时更新排名表
            }
        });
        
        // 省份变化
        $('#province').on('change', function() {
            var province = $(this).val();
            debug('省份选择变化:', province);
            
            if (province) {
                currentMapLevel = 'province';
                currentProvince = province;
                currentCity = '';
                currentDistrict = '';
                
                // 加载该省份的地图数据
                loadProvinceMap(province).then(function() {
                    // 使用新API加载省份详情数据
                    loadProvinceCitiesData(province);
                    
                    // 显示返回按钮
                    $('#map-back-btn').show();
                }).catch(function(error) {
                    debug('加载省份地图失败:', error);
                    $('#map-error').text('加载省份地图失败: ' + error).show();
                });
            } else {
                resetMapLevel();
                loadMapData();
                
                // 隐藏返回按钮
                $('#map-back-btn').hide();
            }
        });

        // 地图点击事件（下钻逻辑）
        salaryChart.on('click', function(params) {
            debug('地图点击:', params.name);
            
            // 从历史记录栈顶获取当前显示的地图信息
            var currentMapInfo = historyStack[historyStack.length - 1];
            
            // 对参数名称进行标准化处理，但保留必要的后缀
            var clickedName = params.name;
            // 为了查找和比较，使用去掉后缀的版本
            var clickedNameNoSuffix = clickedName.replace(/(省|市|自治区|区|县|特别行政区)$/, '');
            
            if (currentMapLevel === 'country') {
                // 从全国下钻到省份
                var provinceName = clickedName; // 保留原始名称，包括后缀
                var provinceNameNoSuffix = clickedNameNoSuffix; // 用于查找匹配
                
                // 检查是否有效省份名称
                var province = findProvince(provinceNameNoSuffix);
                
                if (province) {
                    debug('下钻到省份:', provinceName, '行政编码:', province.adcode);
                    currentMapLevel = 'province';
                    currentProvince = province.name; // 使用标准化的名称
                    currentCity = '';
                    currentDistrict = '';
                    $('#province').val(province.name);
                    
                    // 检查是否是直辖市，直辖市直接展示区县数据
                    if (directCities.includes(province.name)) {
                        debug('点击的是直辖市，直接加载区县数据:', province.name);
                        
                        // 加载省份地图
                        loadProvinceMap(province.name).then(function(geoJson) {
                            // 将新的省份地图信息推入历史记录栈
                            if (geoJson) {
                                historyStack.push({
                                    geoJson: geoJson,
                                    displayName: province.name,
                                    level: 'province',
                                    mapName: province.name,
                                    adcode: province.adcode
                                });
                            }
                            
                            // 直接加载直辖市的区县数据，而不是使用loadProvinceCitiesData加载城市数据
                            currentCity = province.name;
                            loadCityDistrictsData(province.name, province.name);
                            
                            // 显示返回按钮
                            $('#map-back-btn').show();
                        }).catch(function(error) {
                            debug('加载直辖市地图失败:', error);
                            $('#map-error').text('加载地图失败: ' + error).show();
                            // 加载失败时恢复全国视图
                            resetMapLevel();
                            loadMapData();
                        });
                    } else {
                        // 对于普通省份，加载省级地图和城市数据
                        loadProvinceMap(province.name).then(function(geoJson) {
                            // 将新的省份地图信息推入历史记录栈
                            if (geoJson) {
                                historyStack.push({
                                    geoJson: geoJson,
                                    displayName: province.name,
                                    level: 'province',
                                    mapName: province.name,
                                    adcode: province.adcode
                                });
                            }
                            
                            // 使用新API加载省份详情数据
                            loadProvinceCitiesData(province.name);
                            
                            // 显示返回按钮
                            $('#map-back-btn').show();
                        }).catch(function(error) {
                            debug('加载省份地图失败:', error);
                            $('#map-error').text('加载省份地图失败: ' + error).show();
                            // 加载失败时恢复全国视图
                            resetMapLevel();
                            loadMapData();
                        });
                    }
                } else {
                    debug('未找到省份信息，尝试使用硬编码映射:', provinceName);
                    // 尝试在硬编码数据中查找
                    var hardcodedProvince = hardcodedProvinces.find(function(p) {
                        var pName = p.name.replace(/(省|市|自治区)$/, '');
                        return pName === provinceNameNoSuffix || 
                               provinceNameNoSuffix === p.name;
                    });
                    
                    if (hardcodedProvince) {
                        debug('在硬编码数据中找到省份:', hardcodedProvince);
                        currentMapLevel = 'province';
                        currentProvince = hardcodedProvince.name;
                        currentCity = '';
                        currentDistrict = '';
                        $('#province').val(hardcodedProvince.name);
                        
                        loadProvinceMap(hardcodedProvince.name).then(function(geoJson) {
                            // 将新的省份地图信息推入历史记录栈
                            if (geoJson) {
                                historyStack.push({
                                    geoJson: geoJson,
                                    displayName: hardcodedProvince.name,
                                    level: 'province',
                                    mapName: hardcodedProvince.name,
                                    adcode: hardcodedProvince.adcode
                                });
                            }
                            
                            // 使用新API加载省份详情数据
                            loadProvinceCitiesData(hardcodedProvince.name);
                            
                            // 显示返回按钮
                            $('#map-back-btn').show();
                        }).catch(function(error) {
                            debug('加载省份地图失败:', error);
                            alert('无法加载该省份地图，请选择其他省份');
                            resetMapLevel();
                            loadMapData();
                        });
                    }
                }
            } else if (currentMapLevel === 'province') {
                // 从省份下钻到城市
                
                // 检查是否是直辖市，直辖市直接展示区县数据
                if (directCities.includes(currentProvince)) {
                    debug('点击直辖市中的区县:', clickedName);
                    // 加载直辖市的区县数据，保留区县名称（包含"区"、"县"等后缀）
                    loadCityDistrictsData(currentProvince, clickedName);
                    currentMapLevel = 'district';
                    currentCity = currentProvince;
                    currentDistrict = clickedName;
                } else {
                    // 对于普通省份，展示城市数据
                    var cityName = clickedName; // 保留完整城市名称，包括"市"后缀
                    debug('点击省份中的城市:', cityName);
                    
                    // 有些城市可能没有独立地图，可以显示弹窗数据
                    var cityData = mapData.find(function(item) {
                        var itemNameNoSuffix = item.name.replace(/(市|区|县)$/, '');
                        return item.name === cityName || 
                               itemNameNoSuffix === clickedNameNoSuffix;
                    });
                    
                    if (cityData) {
                        // 尝试加载城市地图
                        loadCityMap(cityName).then(function(geoJson) {
                            // 将新的城市地图信息推入历史记录栈，记录父省份
                            if (geoJson) {
                                historyStack.push({
                                    geoJson: geoJson,
                                    displayName: cityName,
                                    level: 'city',
                                    mapName: cityName,
                                    parentName: currentProvince
                                });
                            }
                            
                            // 加载城市区县数据
                            loadCityDistrictsData(currentProvince, cityName);
                            currentMapLevel = 'city';
                            currentCity = cityName;
                            currentDistrict = '';
                        }).catch(function(error) {
                            debug('加载城市地图失败:', error);
                            // 如果无法加载地图，至少显示数据
                            var valueText = currentMetric === 'salary' ? 
                                            cityData.value + ' 元/月' : 
                                            cityData.value + ' 个岗位';
                            alert(cityName + ': ' + valueText);
                        });
                    } else {
                        alert(cityName + ': 暂无数据');
                    }
                }
            } else if (currentMapLevel === 'city') {
                // 从城市下钻到区县
                var districtName = clickedName; // 保留完整区县名称，包括"区"、"县"后缀
                debug('点击城市中的区县:', districtName);
                
                // 显示区县的详细数据
                var districtData = mapData.find(function(item) {
                    var itemNameNoSuffix = item.name.replace(/(区|县)$/, '');
                    return item.name === districtName || 
                           itemNameNoSuffix === clickedNameNoSuffix;
                });
                
                if (districtData) {
                    var valueText = currentMetric === 'salary' ? 
                                    districtData.value + ' 元/月' : 
                                    districtData.value + ' 个岗位';
                    alert(districtName + ': ' + valueText);
                    
                    currentMapLevel = 'district';
                    currentDistrict = districtName;
                } else {
                    alert(districtName + ': 暂无数据');
                }
            }
        });

        // 窗口大小变化时，重新调整地图大小
        $(window).resize(function() {
            if (salaryChart) {
                salaryChart.resize();
            }
        });
    }
    
    /**
     * 在GeoJSON中查找指定名称的地理要素
     * @param {Object} geoJson - GeoJSON对象
     * @param {string} name - 要查找的地理名称
     * @returns {Object|null} - 找到的地理要素或null
     */
    function findFeatureByName(geoJson, name) {
        if (!geoJson || !geoJson.features) {
            return null;
        }
        
        // 规范化名称
        name = name.replace(/(省|市|自治区|区|县|特别行政区)$/, '');
        
        for (var i = 0; i < geoJson.features.length; i++) {
            var feature = geoJson.features[i];
            
            // 尝试不同的属性名来匹配名称
            var featureName = feature.properties.name || 
                             feature.properties.NAME || 
                             feature.name || 
                             '';
                             
            // 规范化特征名称
            featureName = featureName.replace(/(省|市|自治区|区|县|特别行政区)$/, '');
            
            if (featureName === name) {
                return feature;
            }
        }
        
        return null;
    }
    
    /**
     * 使用adcode加载省份地图
     */
    function loadProvinceMapByAdcode(provinceName, adcode) {
        return new Promise(function(resolve, reject) {
            // 规范化省份名称
            provinceName = provinceName.replace(/(省|市|自治区)$/, '');
            
            // 如果已经加载过该省份地图，直接使用缓存
            if (geoJsonData.province[adcode]) {
                debug('使用缓存的省份地图:', provinceName, adcode);
                
                // 确保地图已注册
                if (!registeredMaps[provinceName]) {
                    echarts.registerMap(provinceName, geoJsonData.province[adcode]);
                    registeredMaps[provinceName] = true;
                }
                
                resolve(geoJsonData.province[adcode]);
                return;
            }
            
            debug('加载省份地图:', provinceName, '编码:', adcode);
            
            // 加载省份GeoJSON
            $.ajax({
                url: '/static/geojson/province/' + adcode + '.json',
                type: 'GET',
                dataType: 'json',
                success: function(geoJson) {
                    try {
                        // 保存到缓存
                        geoJsonData.province[adcode] = geoJson;
                        
                        // 注册GeoJSON到ECharts
                        echarts.registerMap(provinceName, geoJson);
                        registeredMaps[provinceName] = true;
                        debug('成功注册省份地图:', provinceName);
                        resolve(geoJson);
                    } catch (e) {
                        debug('注册省份地图失败:', e);
                        reject('注册地图失败: ' + e.message);
                    }
                },
                error: function(xhr, status, error) {
                    debug('加载省份地图失败:', error);
                    reject('加载地图数据失败: ' + error);
                }
            });
        });
    }
    
    /**
     * 使用adcode加载城市地图
     */
    function loadCityMapByAdcode(cityName, adcode) {
        return new Promise(function(resolve, reject) {
            // 规范化城市名称
            cityName = cityName.replace(/(市|区|县)$/, '');
            
            // 如果已经加载过该城市地图，直接使用缓存
            if (geoJsonData.city[adcode]) {
                debug('使用缓存的城市地图:', cityName, adcode);
                
                // 确保地图已注册
                if (!registeredMaps[cityName]) {
                    echarts.registerMap(cityName, geoJsonData.city[adcode]);
                    registeredMaps[cityName] = true;
                }
                
                resolve(geoJsonData.city[adcode]);
                return;
            }
            
            debug('加载城市地图:', cityName, '编码:', adcode);
            
            // 加载城市GeoJSON
            $.ajax({
                url: '/static/geojson/citys/' + adcode + '.json',
                type: 'GET',
                dataType: 'json',
                success: function(geoJson) {
                    try {
                        // 保存到缓存
                        geoJsonData.city[adcode] = geoJson;
                        
                        // 注册GeoJSON到ECharts
                        echarts.registerMap(cityName, geoJson);
                        registeredMaps[cityName] = true;
                        debug('成功注册城市地图:', cityName);
                        resolve(geoJson);
                    } catch (e) {
                        debug('注册城市地图失败:', e);
                        reject('注册地图失败: ' + e.message);
                    }
                },
                error: function(xhr, status, error) {
                    debug('加载城市地图失败:', error);
                    reject('加载地图数据失败，adcode: ' + adcode);
                }
            });
        });
    }
    
    /**
     * 重置地图级别到全国
     */
    function resetMapLevel() {
        debug('重置地图级别到全国');
        currentMapLevel = 'country';
        currentProvince = '';
        currentCity = '';
        currentDistrict = '';
        $('#province').val('');
        
        // 清空历史记录栈，重新添加全国地图
        historyStack = [{
            geoJson: geoJsonData.china,
            displayName: '全国',
            level: 'country',
            mapName: 'china',
            adcode: '100000'  // 虚拟的全国adcode
        }];
    }
    
    /**
     * 加载省份地图数据
     */
    function loadProvinceMap(provinceName) {
        return new Promise(function(resolve, reject) {
            // 规范化省份名称
            var originalProvinceName = provinceName;
            provinceName = provinceName.replace(/(省|市|自治区)$/, '');
            
            // 检查是否是直辖市
            var isDirectCity = directCities.includes(provinceName);
            
            // 如果已经加载过该省份地图，直接使用缓存
            if (registeredMaps[provinceName]) {
                debug('使用缓存的省份地图:', provinceName);
                
                // 如果有缓存的GeoJSON数据，则返回它
                if (geoJsonData.province[provinceName]) {
                    resolve(geoJsonData.province[provinceName]);
                } else {
                    resolve(null); // 没有缓存GeoJSON但地图已注册
                }
                return;
            }
            
            // 查找省份编码
            var province = findProvince(provinceName);
            if (!province) {
                debug('未找到省份:', provinceName);
                for (var i = 0; i < hardcodedProvinces.length; i++) {
                    var item = hardcodedProvinces[i];
                    var itemName = item.name.replace(/(省|市|自治区)$/, '');
                    if (itemName === provinceName) {
                        province = hardcodedProvinces[i];
                        break;
                    }
                }
                if (!province) {
                    reject('未找到省份信息: ' + provinceName);
                    return;
                }
            }
            
            debug('加载省份地图:', provinceName, '编码:', province.adcode);
            
            // 加载省份GeoJSON
            $.ajax({
                url: '/static/geojson/province/' + province.adcode + '.json',
                type: 'GET',
                dataType: 'json',
                success: function(geoJson) {
                    try {
                        // 缓存GeoJSON数据
                        geoJsonData.province[provinceName] = geoJson;
                        
                        // 注册GeoJSON到ECharts
                        echarts.registerMap(provinceName, geoJson);
                        registeredMaps[provinceName] = true;
                        debug('成功注册省份地图:', provinceName);
                        resolve(geoJson);
                    } catch (e) {
                        debug('注册省份地图失败:', e);
                        reject('注册地图失败: ' + e.message);
                    }
                },
                error: function(xhr, status, error) {
                    debug('加载省份地图失败，尝试使用备用方法:', error);
                    
                    // 对于直辖市，尝试使用城市地图
                    if (isDirectCity) {
                        debug('尝试加载直辖市地图:', provinceName);
                        loadCityMapByAdcode(provinceName, province.adcode).then(function(geoJson) {
                            debug('成功从城市地图中加载直辖市地图:', provinceName);
                            
                            // 缓存GeoJSON数据到省份缓存中
                            geoJsonData.province[provinceName] = geoJson;
                            
                            // 注册GeoJSON到ECharts
                            if (!registeredMaps[provinceName]) {
                                echarts.registerMap(provinceName, geoJson);
                                registeredMaps[provinceName] = true;
                            }
                            
                            resolve(geoJson);
                        }).catch(function(error) {
                            debug('直辖市地图也加载失败:', error);
                            reject('加载地图数据失败: ' + error);
                        });
                    } else {
                        reject('加载地图数据失败: ' + error);
                    }
                }
            });
        });
    }
    
    /**
     * 根据省份名称查找省份信息
     */
    function findProvince(provinceName) {
        // 先尝试从location数据中查找
        if (locationData && locationData.provinceList && locationData.provinceList.length > 0) {
            var found = locationData.provinceList.find(function(province) {
                return province.name === provinceName;
            });
            
            if (found) {
                debug('在locationData中找到省份:', provinceName);
                return found;
            }
        }
        
        // 如果在location数据中未找到，则从硬编码数据查找
        var hardcodedFound = hardcodedProvinces.find(function(province) {
            return province.name === provinceName;
        });
        
        if (hardcodedFound) {
            debug('在硬编码数据中找到省份:', provinceName);
            return hardcodedFound;
        }
        
        debug('未找到省份信息:', provinceName);
        return null;
    }
    
    /**
     * 根据城市名称获取所属省份名称（使用硬编码映射）
     */
    function getProvinceByCity(cityName) {
        var province = cityToProvince[cityName];
        debug('获取城市所属省份:', {cityName: cityName, provinceName: province});
        return province;
    }
    
    /**
     * 根据筛选条件加载地图数据
     */
    function loadMapData() {
        // 检查地图是否已注册
        if (currentMapLevel === 'country' && !registeredMaps.china) {
            debug('全国地图未注册');
            return;
        } else if (currentMapLevel === 'province' && !registeredMaps[currentProvince]) {
            debug('省份地图未注册:', currentProvince);
            return;
        } else if (currentMapLevel === 'city' && !registeredMaps[currentCity]) {
            debug('城市地图未注册:', currentCity);
            return;
        }
        
        // 显示加载中
        $('#map-loading').show();
        salaryChart.showLoading({
            text: '数据加载中...',
            color: '#4e73df',
            textColor: '#4e73df',
            maskColor: 'rgba(255, 255, 255, 0.8)'
        });
        
        // 获取筛选条件
        var jobCategory = $('#jobCategory').val();
        var education = $('#education').val();
        var experience = $('#experience').val();
        var scale = $('#scale').val();
        var metric = $('#metric').val();
        currentMetric = metric;
        
        debug('加载数据，当前级别:', currentMapLevel, '当前省份:', currentProvince, '当前城市:', currentCity);
        
        // 构建API URL
        var apiUrl = '/api/salary-map-data';
        
        // 构建查询参数
        var params = {
            job_table: jobCategory,
            education: education,
            experience: experience,
            scale: scale,
            province: currentProvince,
            city: currentCity,
            level: currentMapLevel,
            metric: currentMetric
        };
        
        debug('API请求参数:', params);
        
        // 发送AJAX请求
        $.ajax({
            url: apiUrl,
            type: 'GET',
            data: params,
            dataType: 'json',
            success: function(response) {
                // 隐藏加载提示
                salaryChart.hideLoading();
                $('#map-loading').hide();
                
                debug('API响应:', response);
                
                if (response.code === 0) {
                    // 保存数据
                    var responseData = response.data[currentMetric] || [];
                    mapData = responseData;
                    rankData = response.data.ranking || [];
                    
                    debug('获取数据条数:', mapData.length);
                    debug('地图数据详情:', mapData);
                    
                    // 处理数据，确保value字段是有效数字并且有正确的名称
                    processMapData(mapData);
                    
                    // 更新地图标题
                    updateMapTitle();
                    
                    // 渲染地图和排名表
                    renderMap();
                    renderRankingTable();
                } else {
                    console.error('API错误:', response.message);
                    alert('获取数据失败: ' + (response.message || '未知错误'));
                }
            },
            error: function(xhr, status, error) {
                salaryChart.hideLoading();
                $('#map-loading').hide();
                console.error('AJAX请求失败:', error);
                alert('网络请求失败，请检查网络连接');
            }
        });
    }
    
    /**
     * 处理地图数据，确保value字段有效且名称正确
     */
    function processMapData(data) {
        if (!data || !data.length) return [];
        
        debug('处理前的地图数据:', data);
        
        var processedData = data.map(function(item) {
            // 创建新对象避免修改原始数据
            var newItem = { ...item };
            
            // 确保value是数字
            if (newItem.value === null || newItem.value === undefined || isNaN(newItem.value)) {
                newItem.value = 0;
            } else {
                newItem.value = Number(newItem.value);
            }
            
            // 地名处理：保留原始名称，确保能与地图GeoJSON文件匹配
            // 注意：不要去除名称后缀，除非确认地图文件中的名称不包含这些后缀
            if (newItem.name) {
                // 检查当前级别
                if (currentMapLevel === 'country') {
                    // 全国地图显示时，可以简化省份名称（去掉"省"、"自治区"等后缀）
                    newItem.name = getFullProvinceName(newItem.name);
                }
                // 在省级和城市级别，保留"市"后缀，但可以简化其他后缀
                // 在区县级别，完全保留原始名称
            }
            
            return newItem;
        });
        
        debug('处理后的地图数据:', processedData);
        
        // 更新全局mapData
        mapData = processedData;
        
        return processedData;
    }
    
    /**
     * 更新地图标题
     */
    function updateMapTitle() {
        var metricText = currentMetric === 'salary' ? '平均薪资' : '岗位数量';
        var titleText = '';
        
        if (currentMapLevel === 'country') {
            titleText = '全国' + metricText + '分布';
        } else if (currentMapLevel === 'province') {
            titleText = currentProvince + metricText + '分布';
        } else if (currentMapLevel === 'city') {
            titleText = currentProvince + ' - ' + currentCity + metricText + '分布';
        } else if (currentMapLevel === 'district') {
            titleText = currentCity + ' - ' + currentDistrict + metricText + '分布';
        }
        
        $('.card-header h6').first().text(titleText);
        
        // 更新排名表指标列标题
        if (currentMetric === 'salary') {
            $('#rankMetric').text('平均薪资(元/月)');
        } else {
            $('#rankMetric').text('岗位数量(个)');
        }
    }
    
    /**
     * 渲染地图
     */
    function renderMap() {
        if (!mapData || mapData.length === 0) {
            debug('没有数据可以渲染地图');
            salaryChart.clear();
            
            // 显示无数据提示
            salaryChart.setOption({
                title: {
                    text: '暂无数据',
                    left: 'center',
                    top: 'center'
                }
            });
            
            return;
        }

        var maxValue = getMaxValue();
        
        debug('渲染地图，最大值:', maxValue);
        debug('当前地图级别:', currentMapLevel, '当前省份:', currentProvince, '当前城市:', currentCity);
        debug('使用的地图数据:', JSON.stringify(mapData).substring(0, 300) + '...');
        
        // 确定当前使用的地图名称
        var mapName = 'china';
        if (currentMapLevel === 'province') {
            mapName = currentProvince;
        } else if (currentMapLevel === 'city') {
            // 判断是否是直辖市
            if (directCities.includes(currentCity)) {
                // 直辖市使用省份级别的地图
                mapName = currentCity;
            } else if (directCities.includes(currentProvince) && currentProvince === currentCity) {
                // 直辖市的特殊情况，省份和城市名称相同
                mapName = currentProvince;
            } else {
                // 普通城市
                mapName = currentCity;
            }
        } else if (currentMapLevel === 'district') {
            // 区县级一般没有地图，使用城市地图，通过高亮区县来展示
            mapName = currentCity;
        }
        
        debug('使用的地图名称:', mapName);
        debug('当前地图注册状态:', registeredMaps);

        // 确保地图已注册
        if (!registeredMaps[mapName]) {
            debug('地图未注册，无法渲染:', mapName);
            salaryChart.clear();
            salaryChart.setOption({
                title: {
                    text: '地图数据加载中...',
                    left: 'center',
                    top: 'center'
                }
            });
            return;
        }

        // 颜色确定，从蓝色(低)到红色(高)
        var colorRange = ['#1e90ff', '#6495ed', '#00bfff', '#fff68f', '#ffb90f', '#ffa07a', '#ff6347', '#ff0000'];
        
        // 设置地图配置项
        var option = {
            title: {
                text: currentMapLevel === 'country' ? '全国概况' : 
                      currentMapLevel === 'province' ? currentProvince + '地区详情' : 
                      currentMapLevel === 'city' ? currentCity + '详情' :
                      currentDistrict + '详情',
                left: 'center',
                textStyle: {
                    fontSize: 16,
                    color: '#4e73df'
                },
                subtextStyle: {
                    fontSize: 12,
                    color: '#888'
                }
            },
            tooltip: {
                trigger: 'item',
                formatter: function(params) {
                    if (!params.value && params.value !== 0) {
                        return params.name + ': 暂无数据';
                    }
                    
                    var value = params.value;
                    var raw = params.data.rawData; // 原始数据
                    
                    if (currentMetric === 'salary') {
                        return params.name + '<br/>平均薪资: ' + value + ' 元/月' +
                               (raw ? '<br/>岗位数量: ' + raw.count + '<br/>最高薪资: ' + raw.max + '元<br/>最低薪资: ' + raw.min + '元' : '');
                    } else {
                        return params.name + '<br/>岗位数量: ' + value + ' 个' +
                               (raw ? '<br/>平均薪资: ' + raw.value + '元<br/>最高薪资: ' + raw.max + '元<br/>最低薪资: ' + raw.min + '元' : '');
                    }
                }
            },
            visualMap: {
                min: 0,
                max: maxValue,
                text: currentMetric === 'salary' ? ['高', '低'] : ['多', '少'],
                inRange: {
                    color: colorRange
                },
                calculable: true,
                left: 'left',
                top: 'bottom',
                textStyle: {
                    color: '#333'
                }
            },
            series: [
                {
                    name: currentMetric === 'salary' ? '平均薪资' : '岗位数量',
                    type: 'map',
                    map: mapName,
                    roam: true, // 允许缩放和平移
                    zoom: 1.2,  // 初始缩放比例
                    label: {
                        show: true,
                        formatter: function(params) {
                            // 根据当前层级决定如何显示标签
                            if (currentMapLevel === 'country') {
                                // 全国地图显示时，可以简化省份名称（去掉"省"、"自治区"等后缀）
                                return params.name.replace(/(省|自治区|特别行政区|壮族自治区|回族自治区|维吾尔自治区)$/, '');
                            } else if (currentMapLevel === 'province') {
                                // 省份地图显示时，保留"市"后缀，但可以简化其他后缀
                                return params.name; // 或者根据需要进行适当简化
                            } else {
                                // 城市或区县地图显示时，完全保留原始名称
                                return params.name;
                            }
                        },
                        fontSize: 10
                    },
                    emphasis: {
                        label: {
                            show: true,
                            fontSize: 12,
                            fontWeight: 'bold'
                        },
                        itemStyle: {
                            areaColor: '#ffb980'
                        }
                    },
                    data: mapData
                }
            ]
        };
        
        // 应用配置项
        salaryChart.setOption(option, true);
    }
    
    /**
     * 获取最大值，用于可视化映射
     */
    function getMaxValue() {
        if (!mapData || mapData.length === 0) return 100;
        
        var values = mapData.map(function(item) {
            return item.value;
        });
        
        var maxValue = Math.max.apply(null, values);
        
        // 处理特殊情况
        if (!maxValue || maxValue <= 0) {
            if (currentMetric === 'salary') {
                return 20000; // 默认薪资上限
            } else {
                return 10000; // 默认岗位数上限
            }
        }
        
        // 向上取整到合适的数字
        if (currentMetric === 'salary') {
            // 薪资按1000向上取整
            return Math.ceil(maxValue / 1000) * 1000;
        } else {
            // 岗位数按合适的比例向上取整
            if (maxValue < 100) {
                return Math.ceil(maxValue / 10) * 10;
            } else if (maxValue < 1000) {
                return Math.ceil(maxValue / 100) * 100;
            } else {
                return Math.ceil(maxValue / 1000) * 1000;
            }
        }
    }
    
    /**
     * 渲染排名表
     */
    function renderRankingTable() {
        if (!rankData || rankData.length === 0) {
            $('#rankTableBody').html('<tr><td colspan="4" class="text-center">暂无排名数据</td></tr>');
            return;
        }
        
        var tableHtml = '';
        
        rankData.forEach(function(item) {
            var valueToShow = currentMetric === 'salary' ? item.salary : item.job_count;
            var valueUnit = currentMetric === 'salary' ? ' 元/月' : ' 个';
            
            tableHtml += '<tr>';
            tableHtml += '<td>' + item.rank + '</td>';
            tableHtml += '<td>' + item.name + '</td>';
            
            if (currentMetric === 'salary') {
                tableHtml += '<td>' + item.salary + valueUnit + '</td>';
                tableHtml += '<td>' + item.job_count + ' 个</td>';
            } else {
                tableHtml += '<td>' + item.salary + ' 元/月</td>';
                tableHtml += '<td>' + item.job_count + valueUnit + '</td>';
            }
            
            tableHtml += '</tr>';
        });
        
        $('#rankTableBody').html(tableHtml);
    }
    
    /**
     * 导出数据为CSV
     */
    function exportToCSV() {
        if (!rankData || rankData.length === 0) {
            alert('没有数据可导出');
            return;
        }
        
        var csvContent = '排名,地区,平均薪资(元/月),岗位数量(个)\n';
        
        rankData.forEach(function(item) {
            csvContent += item.rank + ',' + item.name + ',' + item.salary + ',' + item.job_count + '\n';
        });
        
        var blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        var link = document.createElement('a');
        
        // 生成文件名
        var fileName = '薪资排名-';
        if (currentMapLevel === 'country') {
            fileName += '全国';
        } else if (currentMapLevel === 'province') {
            fileName += currentProvince;
        } else if (currentMapLevel === 'city') {
            fileName += currentProvince + '-' + currentCity;
        }
        fileName += '-' + new Date().toISOString().slice(0, 10) + '.csv';
        
        if (navigator.msSaveBlob) { // IE 10+
            navigator.msSaveBlob(blob, fileName);
        } else {
            var url = URL.createObjectURL(blob);
            link.href = url;
            link.setAttribute('download', fileName);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }

    /**
     * 加载省份和城市数据
     */
    function loadProvinceCitiesData(provinceName) {
        // 显示加载中
        $('#map-loading').show();
        salaryChart.showLoading({
            text: '数据加载中...',
            color: '#4e73df',
            textColor: '#4e73df',
            maskColor: 'rgba(255, 255, 255, 0.8)'
        });
        
        // 获取筛选条件
        var jobCategory = $('#jobCategory').val();
        var education = $('#education').val();
        var experience = $('#experience').val();
        var scale = $('#scale').val();
        
        debug('加载省份城市数据，省份:', provinceName);
        
        // 构建查询参数
        var params = {
            province: provinceName,
            job_table: jobCategory,
            education: education,
            experience: experience,
            scale: scale
        };
        
        debug('省份城市API请求参数:', params);
        
        // 发送AJAX请求
        $.ajax({
            url: '/api/province-cities',
            type: 'GET',
            data: params,
            dataType: 'json',
            success: function(response) {
                // 隐藏加载提示
                salaryChart.hideLoading();
                $('#map-loading').hide();
                
                debug('省份城市API响应:', response);
                
                if (response.code === 0) {
                    var provinceData = response.data;
                    debug('省份城市详情数据:', provinceData);
                    
                    if (provinceData && provinceData.cities && provinceData.cities.length > 0) {
                        // 更新地图标题和全局数据
                        currentMapLevel = 'province';
                        currentProvince = provinceData.province;
                        
                        // 处理城市数据，将其转换为地图数据格式
                        mapData = provinceData.cities.map(function(city) {
                            return {
                                // 保留完整的地名，不要去掉后缀，确保能与地图匹配
                                name: city.region,
                                value: currentMetric === 'salary' ? city.value : city.count,
                                // 保存原始数据，便于展示
                                rawData: city
                            };
                        });
                        
                        debug('转换后的地图数据:', mapData);
                        
                        // 构建排名数据
                        rankData = provinceData.cities.map(function(city, index) {
                            return {
                                rank: index + 1,
                                // 可以在排名表中去掉后缀，因为这里只用于展示，不影响地图匹配
                                name: city.region.replace(/(市|县|区)$/, ''),
                                salary: city.value,
                                job_count: city.count
                            };
                        });
                        
                        // 按指标值排序
                        rankData.sort(function(a, b) {
                            return currentMetric === 'salary' ? 
                                b.salary - a.salary : 
                                b.job_count - a.job_count;
                        });
                        
                        // 更新排名序号
                        rankData.forEach(function(item, index) {
                            item.rank = index + 1;
                        });
                        
                        // 只保留前10名
                        rankData = rankData.slice(0, 10);
                        
                        // 更新地图标题
                        updateMapTitle();
                        
                        // 渲染地图和排名表
                        renderMap();
                        renderRankingTable();
                    } else {
                        debug('省份没有城市数据，尝试使用标准API');
                        // 如果没有城市数据，尝试使用标准API
                        loadMapData();
                    }
                } else {
                    console.error('省份城市API错误:', response.message);
                    alert('获取省份数据失败: ' + (response.message || '未知错误'));
                    // 出错时使用标准API
                    loadMapData();
                }
            },
            error: function(xhr, status, error) {
                salaryChart.hideLoading();
                $('#map-loading').hide();
                console.error('AJAX请求失败:', error);
                alert('网络请求失败，请检查网络连接');
                // 出错时使用标准API
                loadMapData();
            }
        });
    }

    /**
     * 加载城市区县数据
     */
    function loadCityDistrictsData(provinceName, cityName) {
        // 显示加载中
        $('#map-loading').show();
        salaryChart.showLoading({
            text: '数据加载中...',
            color: '#4e73df',
            textColor: '#4e73df',
            maskColor: 'rgba(255, 255, 255, 0.8)'
        });
        
        // 获取筛选条件
        var jobCategory = $('#jobCategory').val();
        var education = $('#education').val();
        var experience = $('#experience').val();
        var scale = $('#scale').val();
        
        debug('加载城市区县数据，省份:', provinceName, '城市:', cityName);
        
        // 检查是否是直辖市
        var isDirectCity = directCities.includes(provinceName);
        if (isDirectCity) {
            debug('处理直辖市区县数据:', provinceName);
            // 对于直辖市，省份和城市名称相同
            cityName = provinceName;
        }
        
        // 构建查询参数
        var params = {
            province: provinceName,
            city: cityName,
            job_table: jobCategory,
            education: education,
            experience: experience,
            scale: scale
        };
        
        debug('城市区县API请求参数:', params);
        
        // 发送AJAX请求
        $.ajax({
            url: '/api/city-districts',
            type: 'GET',
            data: params,
            dataType: 'json',
            success: function(response) {
                // 隐藏加载提示
                salaryChart.hideLoading();
                $('#map-loading').hide();
                
                debug('城市区县API响应:', response);
                
                if (response.code === 0) {
                    var cityData = response.data;
                    debug('城市区县详情数据:', cityData);
                    
                    if (cityData && cityData.regions && cityData.regions.length > 0) {
                        // 更新地图标题和全局数据
                        if (isDirectCity) {
                            // 对于直辖市，设置当前级别为city
                            currentMapLevel = 'city';
                            currentCity = cityData.city.replace(/(市|县|区)$/, '');
                        } else if (currentProvince === cityName) {
                            // 如果省份名称和城市名称相同（直辖市情况）
                            currentMapLevel = 'city';
                            currentCity = cityName;
                        } else {
                            // 普通城市
                            currentMapLevel = 'city';
                            currentCity = cityData.city.replace(/(市|县|区)$/, '');
                        }
                        
                        // 处理区县数据，将其转换为地图数据格式
                        mapData = cityData.regions.map(function(district) {
                            return {
                                // 保留完整的地名，包括"区"、"县"后缀，以确保能与地图匹配
                                name: district.name,
                                value: currentMetric === 'salary' ? district.value : district.count,
                                // 保存原始数据，便于展示
                                rawData: district
                            };
                        });
                        
                        debug('转换后的地图数据:', mapData);
                        
                        // 构建排名数据
                        rankData = cityData.regions.map(function(district, index) {
                            return {
                                rank: index + 1,
                                // 可以在排名表中去掉后缀，因为这里只用于展示，不影响地图匹配
                                name: district.name.replace(/(区|县)$/, ''),
                                salary: district.value,
                                job_count: district.count,
                                max_salary: district.max,
                                min_salary: district.min
                            };
                        });
                        
                        // 按指标值排序
                        rankData.sort(function(a, b) {
                            return currentMetric === 'salary' ? 
                                b.salary - a.salary : 
                                b.job_count - a.job_count;
                        });
                        
                        // 更新排名序号
                        rankData.forEach(function(item, index) {
                            item.rank = index + 1;
                        });
                        
                        // 只保留前10名
                        rankData = rankData.slice(0, 10);
                        
                        // 更新地图标题
                        updateMapTitle();
                        
                        // 渲染地图和排名表(如果有注册城市地图)
                        if (isDirectCity || registeredMaps[currentCity]) {
                            renderMap();
                        } else {
                            // 如果没有城市地图，显示数据表格
                            renderDistrictsTable(cityData);
                        }
                        renderRankingTable();
                    } else {
                        debug('城市没有区县数据');
                        alert(cityName + '暂无区县数据');
                        // 如果没有区县数据，返回省级视图
                        currentMapLevel = 'province';
                        currentCity = '';
                        loadProvinceCitiesData(provinceName);
                    }
                } else {
                    console.error('城市区县API错误:', response.message);
                    alert('获取城市数据失败: ' + (response.message || '未知错误'));
                    // 出错时返回省级视图
                    currentMapLevel = 'province';
                    currentCity = '';
                    loadProvinceCitiesData(provinceName);
                }
            },
            error: function(xhr, status, error) {
                salaryChart.hideLoading();
                $('#map-loading').hide();
                console.error('AJAX请求失败:', error);
                alert('网络请求失败，请检查网络连接');
                // 出错时返回省级视图
                currentMapLevel = 'province';
                currentCity = '';
                loadProvinceCitiesData(provinceName);
            }
        });
    }

    /**
     * 渲染区县数据表格（当城市地图不可用时使用）
     */
    function renderDistrictsTable(cityData) {
        // 清空地图容器
        $('#salaryMap').empty();
        
        // 创建表格HTML
        var tableHtml = '<div class="p-3">';
        tableHtml += '<h4 class="mb-3">' + cityData.city + '区县数据</h4>';
        tableHtml += '<table class="table table-bordered table-hover">';
        tableHtml += '<thead><tr><th>区县</th><th>平均薪资(元/月)</th><th>岗位数量</th><th>最高薪资</th><th>最低薪资</th></tr></thead>';
        tableHtml += '<tbody>';
        
        // 添加区县数据行
        cityData.regions.forEach(function(district) {
            tableHtml += '<tr>';
            tableHtml += '<td>' + district.name + '</td>';
            tableHtml += '<td>' + district.value + '</td>';
            tableHtml += '<td>' + district.count + '</td>';
            tableHtml += '<td>' + district.max + '</td>';
            tableHtml += '<td>' + district.min + '</td>';
            tableHtml += '</tr>';
        });
        
        tableHtml += '</tbody></table>';
        tableHtml += '<button id="backToCity" class="btn btn-secondary mt-3">返回' + cityData.province + '省级地图</button>';
        tableHtml += '</div>';
        
        // 添加表格到DOM
        $('#salaryMap').html(tableHtml);
        
        // 添加返回按钮事件
        $('#backToCity').on('click', function() {
            currentMapLevel = 'province';
            currentCity = '';
            loadProvinceCitiesData(cityData.province.replace(/(省|自治区)$/, ''));
        });
    }

    /**
     * 加载城市地图数据
     */
    function loadCityMap(cityName) {
        return new Promise(function(resolve, reject) {
            // 规范化城市名称
            var originalCityName = cityName;
            cityName = cityName.replace(/(市|区|县)$/, '');
            
            // 如果已经加载过该城市地图，直接使用缓存
            if (registeredMaps[cityName]) {
                debug('使用缓存的城市地图:', cityName);
                
                // 如果有缓存的GeoJSON数据，则返回它
                if (geoJsonData.city[cityName]) {
                    resolve(geoJsonData.city[cityName]);
                } else {
                    resolve(null); // 没有缓存GeoJSON但地图已注册
                }
                return;
            }
            
            // 城市编码查找 - 根据location.json中的数据
            var cityCode = '';
            
            // 首先从locationData中查找城市的adcode
            if (locationData) {
                debug('从locationData查找城市编码:', cityName);
                
                // 方法1：遍历locationData中的城市列表
                if (locationData.cityList && locationData.cityList.length > 0) {
                    var foundCity = locationData.cityList.find(function(city) {
                        return city.name === cityName || city.name === originalCityName;
                    });
                    
                    if (foundCity && foundCity.adcode) {
                        cityCode = foundCity.adcode;
                        debug('在cityList中找到城市编码:', {name: cityName, adcode: cityCode});
                    }
                }
                
                // 方法2：如果方法1失败，尝试遍历locationData的所有键
                if (!cityCode) {
                    for (var key in locationData) {
                        var item = locationData[key];
                        if (item && (item.name === cityName || item.name === originalCityName) && item.level === 'city') {
                            cityCode = item.adcode;
                            debug('在locationData对象中找到城市编码:', {name: cityName, adcode: cityCode});
                            break;
                        }
                    }
                }
            }
            
            // 方法3：硬编码常见城市的adcode，确保重要城市能找到对应编码
            if (!cityCode) {
                var cityAdcodeMap = {
                    '杭州': '330100',
                    '宁波': '330200',
                    '温州': '330300',
                    '嘉兴': '330400',
                    '湖州': '330500',
                    '绍兴': '330600',
                    '金华': '330700',
                    '衢州': '330800',
                    '舟山': '330900',
                    '台州': '331000',
                    '丽水': '331100'
                    // 可以根据需要添加更多城市
                };
                
                cityCode = cityAdcodeMap[cityName];
                if (cityCode) {
                    debug('在硬编码映射中找到城市编码:', {name: cityName, adcode: cityCode});
                }
            }
            
            debug('加载城市地图:', cityName, '编码:', cityCode || '未找到');
            
            // 如果找到了编码，则使用编码加载地图
            if (cityCode) {
                $.ajax({
                    url: '/static/geojson/citys/' + cityCode + '.json',
                    type: 'GET',
                    dataType: 'json',
                    success: function(geoJson) {
                        try {
                            // 缓存GeoJSON数据
                            geoJsonData.city[cityName] = geoJson;
                            
                            // 注册GeoJSON到ECharts
                            echarts.registerMap(cityName, geoJson);
                            registeredMaps[cityName] = true;
                            debug('成功注册城市地图:', cityName);
                            resolve(geoJson);
                        } catch (e) {
                            debug('注册城市地图失败:', e);
                            reject('注册地图失败: ' + e.message);
                        }
                    },
                    error: function(xhr, status, error) {
                        debug('加载城市编码地图失败:', error);
                        // 直接失败，不再尝试使用城市名称作为备选方案
                        reject('加载地图数据失败，请确认 ' + cityCode + '.json 文件存在');
                    }
                });
            } else {
                // 没有找到编码，使用上级地图代替，而不是尝试以城市名称加载
                debug('未找到城市 ' + cityName + ' 的编码，无法加载地图');
                reject('未找到城市 ' + cityName + ' 的编码，无法加载地图');
            }
        });
    }
}); 