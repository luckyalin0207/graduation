        $(function () {
            var chartDom = document.getElementById('cGetExp');
            var myChart = echarts.init(chartDom, null, { renderer: 'svg' });
            var option;

            myChart.showLoading();
            $.ajax({
                url: '/cGetExp',
                success: function (data) {
                    var json_data = JSON.parse(data);
                    
                    // 对数据进行筛选，只显示占比较大的项目
                    var threshold = 0.05; // 设置阈值为5%
                    var total = 0;
                    for (var i = 0; i < json_data.value.length; i++) {
                        total += json_data.value[i];
                    }
                    
                    var filteredNames = [];
                    var filteredValues = [];
                    var otherValue = 0;
                    
                    for (var i = 0; i < json_data.name.length; i++) {
                        if (json_data.value[i] / total >= threshold) {
                            filteredNames.push(json_data.name[i]);
                            filteredValues.push(json_data.value[i]);
                        } else {
                            otherValue += json_data.value[i];
                        }
                    }
                    
                    // 如果有其他小项目，将其合并为"其他"
                    if (otherValue > 0) {
                        filteredNames.push("其他");
                        filteredValues.push(otherValue);
                    }
                    
                    // 组装图表数据
                    var objdata = [];
                    for (var i = 0; i < filteredNames.length; i++) {
                        var obj = {};
                        obj.value = filteredValues[i];
                        obj.name = filteredNames[i];
                        objdata.push(obj);
                    }
                    
                    option = {
                        title: {
                            text: 'C/C++经验要求分布',
                            left: 'center'
                        },
                        tooltip: {
                            trigger: 'item',
                            formatter: '{a} <br/>{b}: {c} ({d}%)'
                        },
                        legend: {
                            orient: 'horizontal',
                            bottom: 10,
                            left: 'center',
                            type: 'scroll',
                            pageButtonItemGap: 5,
                            pageButtonGap: 5,
                            pageIconSize: 12
                        },
                        series: [
                            {
                                name: '岗位数',
                                type: 'pie',
                                radius: '65%',
                                avoidLabelOverlap: true,
                                itemStyle: {
                                    borderRadius: 6,
                                    borderColor: '#fff',
                                    borderWidth: 2
                                },
                                label: {
                                    show: true,
                                    formatter: '{b}: {d}%'
                                },
                                emphasis: {
                                    label: {
                                        show: true,
                                        fontSize: '14',
                                        fontWeight: 'bold'
                                    }
                                },
                                data: objdata
                            }
                        ]
                    };

                    myChart.hideLoading();
                    option && myChart.setOption(option);
                    // 图表自适应容器
                    window.addEventListener("resize", function () {
                        $('#cGetExp').width('100%');
                        myChart.resize();
                    });
                }
            })
        })

