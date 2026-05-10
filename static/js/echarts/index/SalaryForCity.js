$(function () {
            var chartDom = document.getElementById('SalaryForCity');
            var myChart = echarts.init(chartDom,null,{ renderer : 'svg' });
            var option;

            myChart.showLoading();
            $.ajax({
                url:'/getSalaryForCity', //转化字符串
                success: function (data) { //成功的话，得到消
                    var json_data = JSON.parse(data);
                let dataAxis = json_data.name;
                // prettier-ignore
                let data1 = json_data.value;
                let yMax = 50000;
                let dataShadow = [];
                for (let i = 0; i < data1.length; i++) {
                  dataShadow.push(yMax);
                }
                option = {
                  title: {
                    text: '城市平均待遇',
                    subtext: '                                    单位(元)'
                  },
                  xAxis: {
                    data: dataAxis,
                    axisLabel: {
                      inside: true,
                      color: '#fff'
                    },
                    axisTick: {
                      show: false
                    },
                    axisLine: {
                      show: false
                    },
                    z: 10
                  },
                  yAxis: {
                    axisLine: {
                      show: false
                    },
                    axisTick: {
                      show: false
                    },
                    axisLabel: {
                      color: '#999'
                    }
                  },
                  dataZoom: [
                    {
                      type: 'inside'
                    }
                  ],
                  series: [
                    {
                      type: 'bar',
                      showBackground: true,
                      itemStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                          { offset: 0, color: '#12C2E9'},
                          { offset: 0.5, color: '#C471ED' },
                          { offset: 1, color: '#F64F59' }
                        ])
                      },
                      emphasis: {
                        itemStyle: {
                          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: '#12C2E9' },
                            { offset: 0.7, color: '#C471ED' },
                            { offset: 1, color: '#F64F59' }
                          ])
                        }
                      },
                      data: data1,
                         itemStyle: {
                             normal: {
                                 label: {
                                     show: true,		//开启显示
                                     position: 'top',	//在上方显示
                                     textStyle: {	    //数值样式
                                         color: 'black',
                                         fontSize: 16
                                     }
                                 }
                             }
                         }

                    }
                  ]
                };
            // Enable data zoom when user click bar.
            const zoomSize = 6;
            myChart.on('click', function (params) {
              console.log(dataAxis[Math.max(params.dataIndex - zoomSize / 2, 0)]);
              myChart.dispatchAction({
                type: 'dataZoom',
                startValue: dataAxis[Math.max(params.dataIndex - zoomSize / 2, 0)],
                endValue:
                  dataAxis[Math.min(params.dataIndex + zoomSize / 2, data1.length - 1)]
              });
            });



                    myChart.hideLoading();
                    option && myChart.setOption(option);
                     // 图表自适应容器
                    window.addEventListener("resize",function() {
                        $('#SalaryForCity').width('100%');
                        myChart.resize();
                    });

                }
            })
        })