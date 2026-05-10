        $(function () {
            var chartDom = document.getElementById('radar');
            var myChart = echarts.init(chartDom,null,{ renderer : 'svg' });
            var option;

            myChart.showLoading();
            $.ajax({
                url:'/radar', //转化字符串
                success: function (data) { //成功的话，得到消
                    var json_data = JSON.parse(data);
                    var obj_data = [];
                    for (var i = 0; i < json_data.name.length; i++){
                        var obj = {};
                        obj.value = json_data.value[i];
                        obj.name = json_data.name[i];
                        obj_data.push(obj);
                    }
                     option = {

                          legend: {
                            data: json_data.name
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
                              type: 'radar',
                              data: obj_data
                            }
                          ]
                        };


                    myChart.hideLoading();
                    option && myChart.setOption(option);
                     // 图表自适应容器
                    window.addEventListener("resize",function(){
                        $('#radar').width('100%');
                        myChart.resize();
                    });

                }
            })
        })

