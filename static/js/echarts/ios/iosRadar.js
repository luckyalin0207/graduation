        $(function () {
            var chartDom = document.getElementById('iosRadar');
            var myChart = echarts.init(chartDom, null, { renderer: 'svg' });
            var option;

            myChart.showLoading();
            $.ajax({
                url: '/iosRadar',
                success: function (data) {
                    var json_data = JSON.parse(data);
                    
                    // 对数据进行标准化处理，确保各维度相对均衡
                    var standardized_values = [];
                    var raw_values = json_data.value;
                    
                    // 对最大值不合理的数据进行处理，特别是岗位数量
                    if (raw_values[5] > 5) {
                        // 使用对数变换来压缩大数值
                        raw_values[5] = 4 + Math.log10(raw_values[5]/5);
                    }
                    
                    // 平均薪资和最高薪资可能也需要调整，确保它们不会过大
                    if (raw_values[1] > 2) raw_values[1] = 2; // 最高薪资
                    if (raw_values[2] > 2) raw_values[2] = 2; // 平均薪资
                    
                    // 复制处理过的数据
                    standardized_values = raw_values.slice();
                    
                    option = {
                        title: {
                            text: 'iOS岗位属性分析'
                        },
                        tooltip: {
                            trigger: 'item',
                            formatter: function(params) {
                                return params.name + '<br/>' + params.marker + params.seriesName + '：' + params.value;
                            }
                        },
                        radar: {
                            shape: 'polygon',
                            indicator: [
                                { name: '最低薪资', max: 10 },
                                { name: '最高薪资', max: 2 },
                                { name: '平均薪资', max: 2 },
                                { name: '经验要求', max: 1 },
                                { name: '学历要求', max: 1 },
                                { name: '岗位数量', max: 6 }
                            ]
                        },
                        series: [
                            {
                                name: 'iOS岗位特性',
                                type: 'radar',
                                areaStyle: {
                                    opacity: 0.5
                                },
                                lineStyle: {
                                    width: 2
                                },
                                symbolSize: 5,
                                data: [
                                    {
                                        value: standardized_values,
                                        name: 'iOS指标',
                                        itemStyle: {
                                            color: '#3498db' // 蓝色系
                                        }
                                    }
                                ]
                            }
                        ]
                    };

                    myChart.hideLoading();
                    option && myChart.setOption(option);
                    // 图表自适应容器
                    window.addEventListener("resize", function () {
                        $('#iosRadar').width('100%');
                        myChart.resize();
                    });
                }
            })
        })

