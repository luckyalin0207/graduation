$(function () {
            var chartDom = document.getElementById('javaGetEduForSalary');
            var myChart = echarts.init(chartDom,null,{ renderer : 'svg' });


            var option;
            myChart.showLoading();
            $.ajax({
                url:'/javaGetEduForSalary', //转化字符串
                success: function (data) { //成功的话，得到消
                    let json_data = JSON.parse(data);
                    let objdata = [];
                    objdata.push(['product', '最低薪资', '平均薪资', '最高薪资'])
                    for (var i = 0; i < json_data.name.length; i++){
                        var obj = [];
                        obj.push(json_data.name[i])
                        obj.push(json_data.value[i][0])
                        obj.push(json_data.value[i][1])
                        obj.push(json_data.value[i][2])
                        objdata.push(obj);
                    }
                   option = {
                      legend: {},
                      tooltip: {},
                      dataset: {
                        source: objdata
                      },
                      xAxis: { type: 'category' },
                      yAxis: {  name:'¥/月'
                        },
                      // Declare several bar series, each will be mapped
                      // to a column of dataset.source by default.
                      series: [{ type: 'bar' }, { type: 'bar' }, { type: 'bar' }]
                    };

                    myChart.hideLoading();

                    option && myChart.setOption(option);
                    // 图表自适应容器
                    window.addEventListener("resize",function(){
                        $('#javaGetEduForSalary').width('100%');
                        myChart.resize();
                    });

                }
            })
        })
