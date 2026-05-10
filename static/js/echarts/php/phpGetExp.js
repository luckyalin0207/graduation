        $(function () {
            var chartDom = document.getElementById('phpGetExp');
            var myChart = echarts.init(chartDom,null,{ renderer : 'svg' });
            var option;

            myChart.showLoading();
            $.ajax({
                url:'/phpGetExp', //转化字符串
                success: function (data) { //成功的话，得到消
                    var json_data = JSON.parse(data);
                    var objdata = [];
                    for (var i = 0; i < json_data.name.length; i++){
                        var obj = {};
                        obj.value = json_data.value[i];
                        obj.name = json_data.name[i];
                        objdata.push(obj);
                    }
                     option = {
                          title: {
                            left: 'center'
                          },
                          tooltip: {
                            trigger: 'item'
                          },
                          legend: {
                            orient: 'vertical',
                            left: 'right'
                          },
                          series: [
                            {
                              name: '岗位数',
                              type: 'pie',
                              radius: '75%',
                              data: objdata,
                              emphasis: {
                                itemStyle: {
                                  shadowBlur: 10,
                                  shadowOffsetX: 0,
                                  shadowColor: 'rgba(0, 0, 0, 0.5)'
                                }
                              }
                            }
                          ]
                     };

                    myChart.hideLoading();
                    option && myChart.setOption(option);
                     // 图表自适应容器
                    window.addEventListener("resize",function(){
                        $('#phpGetExp').width('100%');
                        myChart.resize();
                    });

                }
            })
        })

