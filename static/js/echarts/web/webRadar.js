        $(function () {
            var chartDom = document.getElementById('webRadar');
            var myChart = echarts.init(chartDom,null,{ renderer : 'svg' });
            var option;

            myChart.showLoading();
            $.ajax({
                url:'/webRadar', //转化字符串
                success: function (data) { //成功的话，得到消
                    var json_data = JSON.parse(data);
                     option = {
                          title: {
                            text: 'WEB岗位属性'
                          },
                          legend: {
                            data: ['Allocated Budget', 'Actual Spending']
                          },
                          radar: {
                            // shape: 'circle',
                            indicator: [
                              { name: '最低薪资', max: 10 },
                              { name: '最高薪资', max: 1 },
                              { name: '平均薪资', max: 1.5 },
                              { name: '经验要求', max: 1 },
                              { name: '学历要求', max: 1 },
                              { name: '岗位数量', max: 15 }
                            ]
                          },
                          series: [
                            {
                              name: 'Budget vs spending',
                              type: 'radar',
                                areaStyle: {},
                                 symbolSize: 0,
                              data: [
                                {
                                  value: json_data.value
                                },
                              ]
                            }
                          ]
                        };


                    myChart.hideLoading();
                    option && myChart.setOption(option);
                     // 图表自适应容器
                    window.addEventListener("resize",function(){
                        $('#webRadar').width('100%');
                        myChart.resize();
                    });

                }
            })
        })

