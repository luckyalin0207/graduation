        $(function () {
            var chartDom = document.getElementById('testRadar');
            var myChart = echarts.init(chartDom,null,{ renderer : 'svg' });
            var option;

            myChart.showLoading();
            $.ajax({
                url:'/testRadar', //转化字符串
                success: function (data) { //成功的话，得到消
                    var json_data = JSON.parse(data);
                    
                    // 对数据进行标准化处理，确保各维度相对均衡
                    var standardized_values = [];
                    var raw_values = json_data.value;
                    
                    // 处理岗位数量（第6个数据），限制其最大值为5
                    if (raw_values[5] > 5) {
                        raw_values[5] = 5 + Math.log(raw_values[5] - 4);
                    }
                    
                    // 复制处理过的数据
                    standardized_values = raw_values.slice();
                    
                    option = {
                        title: {
                            text: '测试岗位属性'
                        },
                        tooltip: {
                            trigger: 'item'
                        },
                        radar: {
                            shape: 'polygon',
                            indicator: [
                                { name: '最低薪资', max: 10 },
                                { name: '最高薪资', max: 2 },
                                { name: '平均薪资', max: 2 },
                                { name: '经验要求', max: 1 },
                                { name: '学历要求', max: 1 },
                                { name: '岗位数量', max: 7 }
                            ]
                        },
                        series: [
                            {
                                name: '测试岗位属性分析',
                                type: 'radar',
                                areaStyle: {
                                    opacity: 0.6
                                },
                                symbolSize: 6,
                                data: [
                                    {
                                        value: standardized_values,
                                        name: '测试指标',
                                        itemStyle: {
                                            color: '#7B68EE'
                                        }
                                    }
                                ]
                            }
                        ]
                    };

                    myChart.hideLoading();
                    option && myChart.setOption(option);
                     // 图表自适应容器
                    window.addEventListener("resize",function(){
                        $('#testRadar').width('100%');
                        myChart.resize();
                    });
                }
            })
        })

